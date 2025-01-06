import time
import pandas as pd
import numpy as np
import pyvisa
import pymeasure
import re
from pymeasure.instruments.keithley import Keithley2450
import logging
import csv
import io
import streamlit as st 

def auto_detect_keithley():
    """Detect Keithley 2450 and return its resource name."""
    rm = pyvisa.ResourceManager()
    instruments = rm.list_resources()
    for instrument in instruments:
        try:
            device = Keithley2450(instrument)
            if "Keithley 2450" in device.id:
                return instrument
        except Exception:
            continue
    raise ConnectionError("No Keithley 2450 detected.")


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class KeithleyBackend:
        
    def __init__(self):
        """Initialize the Keithley 2450 backend."""
        try:
            resource_name = auto_detect_keithley()
            self.instrument = Keithley2450(resource_name)
            self.data = pd.DataFrame()
        except Exception as e:
            raise ConnectionError(f"Unable to connect to Keithley 2450: {e}")

    #def __init__(self, resource_name):
        #"""Initialize the Keithley 2450 backend."""
        #try:
            #self.instrument = Keithley2450(resource_name)
            #self.data = pd.DataFrame()  # To store measurement data
        #except Exception as e:
            #raise ConnectionError(f"Unable to connect to Keithley 2450: {e}")

    def stream_data(self):
        """Stream real-time measurement data."""
        try:
            while True:
                data = self.measure(["Voltage", "Current", "Resistance", "Power"], delay=0.1)
                yield data
        except KeyboardInterrupt:
            log.info("Data streaming stopped by user.")
        finally:
            self.instrument.disable_source()

    def fetch_real_time_data(self):
        """Fetch the most recent measurement data."""
        try:
            if not self.data.empty:
                return self.data.iloc[-1].to_dict()
            else:
                return {}
        except Exception as e:
            log.exception(f"Error fetching data: {e}")
            raise RuntimeError(f"Error fetching data: {e}")


    def configure_source(self, mode, **kwargs):
        """
        Configure the instrument source settings based on the mode.
        Args:
            mode: One of ['Voltage Bias', 'Voltage Sweep', 'Voltage List Sweep', 
                         'Current Bias', 'Current Sweep', 'Current List Sweep']
            kwargs: Additional parameters like voltage/current levels, range, etc.
        """
        try:
            if mode == "Voltage Bias":
                self.instrument.apply_voltage(
                    voltage_range=kwargs.get("voltage_range"),
                    compliance_current=kwargs.get("current_limit", 0.1)
                )
                self.instrument.source_voltage = kwargs["voltage_level"]

            elif mode == "Current Bias":
                self.instrument.apply_current(
                    current_range=kwargs.get("current_range"),
                    compliance_voltage=kwargs.get("voltage_limit", 0.1)
                )
                self.instrument.source_current = kwargs["current_level"]

            elif mode == "Voltage Sweep":
                self.instrument.apply_voltage(
                    voltage_range=kwargs.get("voltage_range"),
                    compliance_current=kwargs.get("current_limit", 0.1)
                )
                self.setup_sweep("voltage", kwargs)

            elif mode == "Current Sweep":
                self.instrument.apply_current(
                    current_range=kwargs.get("current_range"),
                    compliance_voltage=kwargs.get("voltage_limit", 0.1)
                )
                self.setup_sweep("current", kwargs)

            elif mode in ["Voltage List Sweep", "Current List Sweep"]:
                self.upload_list(kwargs["list_file"], mode)

            self.instrument.enable_source()

        except ValueError as e:  # More specific exception handling
            raise ValueError(f"Invalid input parameters for source configuration: {e}")
        except Exception as e:  # Catch any other exceptions during source config
            raise RuntimeError(f"Error configuring source: {e}")
        
    def configure_measurement(self, **kwargs):
        """Configures measurement settings (NPLC, ranges, etc.)."""
        try:
            nplc = kwargs.get("nplc", 1.0) # Default NPLC
            
            def _set_range(measurement_type, range_setting):
                if range_setting == "Auto":
                    if measurement_type == "voltage":
                        self.instrument.auto_range_voltage()  # Enable voltage auto-range for measurement
                    elif measurement_type == "current":
                        self.instrument.auto_range_current() # Enable current auto-range for measurement
                    elif measurement_type == "resistance":
                        pass

                elif range_setting == "Best Fixed":
                    pass #Best Fixed sets automatic voltage and current range by itself

                else:  # Manual range setting
                    match = re.match(r"([0-9.]+)([a-zA-Zμ]+)", range_setting)
                    if match:
                        value = float(match.group(1))
                        unit = match.group(2)
                        if unit.lower() in ("mv", "ma"):
                            value *= 1e-3
                        elif unit.lower() in ("v", "a", "ω"):
                            pass  # No scaling
                        elif unit.lower() in ("kω"):
                            value *= 1e3
                        elif unit.lower() in ("μa",):
                            value *= 1e-6
                        elif unit.lower() in ("na"):
                            value *= 1e-9
                        setattr(self.instrument, f"{measurement_type.lower()}_range", value)
                    else:
                        raise ValueError(f"Invalid {measurement_type} range format: {range_setting}")
            
            measurements = kwargs.get("measurements", [])
            if "Voltage" in measurements:
                _set_range("voltage", kwargs.get("voltage_range", "Auto")) # Using helper
                self.instrument.voltage_nplc = nplc
                self.voltage_type = kwargs.get("voltage_type", "Measured") 
            if "Current" in kwargs.get("measurements", []):
                _set_range("current", kwargs.get("current_range", "Auto"))  # Use helper
                self.instrument.current_nplc = nplc
                self.current_type = kwargs.get("current_type", "Measured") 
            if "Resistance" in kwargs.get("measurements", []):
                _set_range("resistance", kwargs.get("resistance_range", "Auto")) # Use helper
                self.instrument.resistance_nplc = nplc
                self.resistance_type = kwargs.get("resistance_type", "Measured") 
                # Set other resistance settings if needed (e.g., wires)

        except ValueError as e:
            raise ValueError(f"Invalid measurement parameters: {e}")
        except Exception as e:
            log.exception(f"Error configuring measurements: {e}")  # Log unexpected errors
            raise RuntimeError(f"Error configuring measurements: {e}")

    def setup_sweep(self, sweep_type, params):
        """
        Set up a voltage or current sweep.
        Args:
            sweep_type: 'voltage' or 'current'
            params: Sweep parameters (start, stop, steps, delay, sweep_type, dual_sweep, stepper)
        """
        try:
            start = params.get("start", 0.0)
            stop = params.get("stop", 1.0)
            num_steps = params.get("steps", 10)
            delay = params.get("delay", 0.1)
            sweep_type = params.get("sweep_type", "Linear")
            dual_sweep = params.get("dual_sweep", False)
            stepper = params.get("stepper", False)

            if sweep_type == "Linear":
                values = np.linspace(start, stop, num_steps)
            elif sweep_type == "Logarithmic":
                if start <= 0 or stop <= 0:
                    raise ValueError("Logarithmic sweep requires positive start and stop values.")
                values = np.logspace(np.log10(start), np.log10(stop), num_steps)

            # Implement stepper functionality (ensures increments are precise)
            if stepper:  
                step_size = (stop - start) / (num_steps - 1)
                values = np.arange(start, stop + step_size, step_size)

            # Handle dual sweep (forward + reverse)
            if dual_sweep:
                forward_values = values
                reverse_values = values[::-1]
                values = np.concatenate([forward_values, reverse_values])

            if params.get('source_mode') in ["Voltage List Sweep", "Current List Sweep"]: 
                values = np.array(params.get('list_values', []))  # Directly use the uploaded list values.
                stepper = True

            data_list = []
            for value in values:
                try:
                    if sweep_type == "voltage":
                        self.instrument.source_voltage = value
                    elif sweep_type == "current":
                        self.instrument.source_current = value

                    time.sleep(delay)
                    measurement_data = self.measure(params['measurements'], 0)

                # Append measurement to list of dictionaries
                    data_list.append(measurement_data)

                except Exception as e:  # Handle errors within sweep
                    log.exception(f"Error during {sweep_type} sweep at {value}: {e}")
                    if isinstance(e, pymeasure.instruments.InstrumentError): #Example specific pymeasure error handling
                        st.error(f"Instrument error during sweep. Check connections.")
                        raise  # Reraise after logging to stop the measurement

            self.data = pd.DataFrame(data_list) # Dataframe creation outside loop


        except ValueError as e: # Handling the logspace issue for zero and neg values
            raise ValueError(f"Invalid sweep parameters: {e}")
        except Exception as e:
            raise RuntimeError(f"Error setting up {sweep_type} sweep: {e}")

    def upload_list(self, file, mode, params):  # Add 'params' here
        """
        Upload a CSV list for list sweep mode.  
        """
        try:
            if not file:  # Check if file is uploaded
                raise ValueError("No file uploaded")

            values = []
            reader = csv.reader(io.StringIO(file.getvalue().decode("utf-8")))
            next(reader, None)  # Skip header (if present)
            for row in reader:
                try:
                    if not row:  # Handle empty rows
                        continue
                    if len(row) != 1:
                        raise ValueError("Invalid CSV format: Each row must have exactly one value.")
                    values.append(float(row[0]))
                except ValueError as e:
                    log.warning(f"Skipping invalid row in CSV: {row} - {e}")
                    continue  # Skip to the next row

            delay = params.get("delay_seconds", 0.1)

            data_list = []  # Collect data during list sweep
            for value in values:
                try:
                    if mode == "Voltage List Sweep":
                        self.instrument.source_voltage = value
                    elif mode == "Current List Sweep":
                        self.instrument.source_current = value
                    time.sleep(delay)  # Or use the delay from 'params'
                    measurement_data = self.measure(params.get("measurements", []), 0) #Use params here as well for correct measurement settings
                    data_list.append(measurement_data)
                except Exception as e:
                    log.exception(f"Error during {mode} at {value}: {e}")
                    raise  # Re-raise to stop the measurement

            self.data = pd.DataFrame(data_list)

            params['list_values'] = values # store list values for stepper functionality
            params['steps'] = len(values) # Forcing number of steps to be equal to list length
            self.setup_sweep('voltage' if mode == 'Voltage List Sweep' else 'current', params)

        except ValueError as ve:
            raise RuntimeError(f"CSV validation error: {ve}")
        except Exception as e:
            raise RuntimeError(f"Error uploading list: {e}")

    def measure(self, measurements, delay):
        """
        Perform measurements and collect data.
        Args:
            measurements: List of enabled measurements (e.g., ['Voltage', 'Current'])
            delay: Delay between measurements
        """
        try:
            measurement_data = {}  # Corrected data storage
            if "Voltage" in measurements:
                if self.voltage_type == "Programmed":
                    measurement_data["Voltage (V)"] = self.instrument.source_voltage  
                else: 
                    measurement_data["Voltage (V)"] = self.instrument.voltage     
            
            if "Current" in measurements:
                if self.voltage_type == "Programmed":
                    measurement_data["Current (A)"] = self.instrument.source_current  
                else: 
                    measurement_data["Current (A)"] = self.instrument.current     
            
            if "Resistance" in measurements:
                measurement_data["Resistance (Ω)"] = self.instrument.resistance

            if 'Power' in measurements:
                measurement_data['Power (W)'] = measurement_data.get("Voltage (V)", 0) * measurement_data.get("Current (A)", 0)

            if "Timestamp" in measurements:
                measurement_data["Timestamp"] = time.time()

            time.sleep(delay)
            return measurement_data # Return the data instead of appending here
        except Exception as e:
            log.exception(f"Error during measurement: {e}")  # Log the exception
            self.instrument.shutdown()  # added for safe shutdown on error
            raise
        
    def run_measurement(self, settings):
        try:

            input_jacks = settings.get('input_jacks')
            if input_jacks == "Front":
                self.instrument.input_jacks = "front"  # Use lowercase "front"
            elif input_jacks == "Rear":
                self.instrument.input_jacks = "rear"   # Use lowercase "rear"

            sensing_mode = settings.get('sensing_mode')
            if sensing_mode == "2-Wire":
                self.instrument.sensing_mode = "2wire"     # Use "2wire"
            elif sensing_mode == "4-Wire":
                self.instrument.sensing_mode = "4wire"     # Use "4wire"

            output_off_state = settings.get('output_off_state')
            valid_off_states = {   # Mapping for valid values
                "Normal": "normal",
                "High-Z": "highz",
                "Zero": "zero",
                "Guard": "guard" 
            }
            self.instrument.output_off_state = valid_off_states.get(output_off_state, "normal") # Default to "normal"

            high_capacitance = settings.get('high_capacitance')
            self.instrument.high_capacitance = high_capacitance == "On" # Boolean True/False

            offset_compensated_ohms = settings.get('offset_compensated_ohms')
            self.instrument.offset_compensated_ohms = offset_compensated_ohms == "On"

            self.configure_source(settings.get("source_mode"), **settings)
            self.configure_measurement(**settings)
            self.instrument.enable_source()

            data_list = [] # List to store data

            source_mode = settings.get("source_mode")
            if source_mode == "Voltage Bias" or source_mode == "Current Bias":
                num_measurements = settings.get("num_measurements", 1)
                delay = settings.get("delay_seconds", 0.1) 

                for _ in range(num_measurements): # Looping for multiple readings
                    measurement_data = self.measure(settings.get("measurements", []), delay)
                    data_list.append(measurement_data)

            elif source_mode in ["Voltage Sweep", "Current Sweep", "Voltage List Sweep", "Current List Sweep"]: #Sweep and List Sweep already updated with measurement inside loop

                # Get measurements once and save to data frame (already implemented in setup_sweep and upload_list)
                if source_mode in ["Voltage List Sweep", "Current List Sweep"]:
                    self.upload_list(settings["list_file"], source_mode, settings)

                elif source_mode in ["Voltage Sweep", "Current Sweep"]:
                    sweep_type = "voltage" if source_mode == "Voltage Sweep" else "current"
                    self.setup_sweep(sweep_type, settings)
                self.data = self.data

            else:
                raise ValueError(f"Unsupported source mode: {source_mode}")

            if source_mode in ["Voltage Bias", "Current Bias"]:    
                self.data = pd.DataFrame(data_list)

        except Exception as e:
            log.exception(f"Error during measurement: {e}")
            self.data = pd.DataFrame()  # Clear data in case of an error
            raise RuntimeError(f"Error during measurement: {e}")  # More specific error message
        finally:
            self.instrument.disable_source()

    def shutdown(self):
        """Safely shutdown the instrument."""
        try:
            self.instrument.shutdown()
        except Exception as e:
            raise RuntimeError(f"Error shutting down: {e}")

    def export_data(self, format_type):
        """
        Export the measurement data to the specified format.
        Args:
            format_type: 'csv', 'excel', or 'image'
        """
        try:
            if format_type == "csv":
                self.data.to_csv("measurement_data.csv", index=False)
            elif format_type == "excel":
                self.data.to_excel("measurement_data.xlsx", index=False)
            elif format_type == "image":
                import matplotlib.pyplot as plt
                plt.figure()
                self.data.plot()
                plt.savefig("graph_image.png")
        except Exception as e:
            raise RuntimeError(f"Error exporting data: {e}")
 