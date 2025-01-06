import streamlit as st
import matplotlib.pyplot as plt

st.title("Keithley 2450 Interface")
st.sidebar.subheader("Export Options")
st.sidebar.button("Export to Excel")
st.sidebar.button("Export to CSV")
st.sidebar.button("Export Graph Image")

tab1, tab2, tab3 = st.tabs(["Source Measure", "Sheet", "Graph"])

def high_precision_input(label, value=0.0, key=None, format_str="%.12f"):
    input_value = st.text_input(label, value=f"{value:.12f}".rstrip('0').rstrip('.'), key=key)
    try:
        input_value = float(input_value)
        return input_value
    except ValueError:
        st.error("Please enter a valid number")
        return value

data_placeholder = st.empty()
graph_placeholder = st.empty()

def integer_input(label, value=1, key=None):
    return int(st.number_input(label, value=value, min_value=1, step=1, key=key))

def plot_graph(data):
    x_data = [d['Timestamp'] for d in data]
    y_voltage = [d['Voltage (V)'] for d in data]
    y_current = [d['Current (A)'] for d in data]

    fig, ax1 = plt.subplots()
    ax1.plot(x_data, y_voltage, label="Voltage (V)", color="blue")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Voltage (V)", color="blue")

    ax2 = ax1.twinx()
    ax2.plot(x_data, y_current, label="Current (A)", color="red")
    ax2.set_ylabel("Current (A)", color="red")

    return fig

#def real_time_data_update():
    #while st.session_state.get('run_measurement', False):
        #new_data = backend_fetch_data()  # Replace with actual backend function
        #if new_data:
            #st.session_state['data'].append(new_data)
            #data_placeholder.table(st.session_state['data'])
            #graph_placeholder.pyplot(plot_graph(st.session_state['data']))

with tab1:
    st.header("Source Measure Settings")

    col1, col2 = st.columns(2)

    
with col1:
    st.subheader("Source Settings")

    source_mode = st.selectbox("Source Mode", [
        "Voltage Bias", "Voltage Sweep", "Voltage List Sweep", 
        "Current Bias", "Current Sweep", "Current List Sweep"
    ])

    # Voltage Bias mode
    if source_mode == "Voltage Bias":
        voltage_level = high_precision_input("Voltage Level (V)", value=0.0)
        voltage_range = st.selectbox("Voltage Range", ["Auto", "Best Fixed", "200mV", "2.0V", "20.0V", "200.0V"])
        current_limit = high_precision_input("Current Limit (A)", value=0.0)
        num_measurements = integer_input("Number of Measurements", value=10)
        delay_seconds = high_precision_input("Delay Seconds", value=0.1)

    # Voltage Sweep mode with number of steps or step voltage
    elif source_mode == "Voltage Sweep":
        stepper = st.checkbox('Stepper')
        dual_sweep = st.checkbox('Dual Sweep')
        start_voltage = high_precision_input("Start Voltage (V)", value=0.0)
        stop_voltage = high_precision_input("Stop Voltage (V)", value=5.0)

        # User can input either step voltage or number of steps, the other is auto-calculated
        st.subheader("Choose Step Voltage or Number of Steps")
        step_type = st.radio("Input Type", ["Step Voltage", "Number of Steps"])

        if step_type == "Step Voltage":
            step_voltage = high_precision_input("Step Voltage (V)", value=0.05)
            # Automatically calculate number of steps
            num_steps = int((stop_voltage - start_voltage) / step_voltage) + 1
            st.write(f"Number of Steps: {num_steps}")
        else:
            num_steps = integer_input("Number of Steps", value=100)
            # Automatically calculate step voltage
            step_voltage = (stop_voltage - start_voltage) / (num_steps - 1)
            st.write(f"Step Voltage: {step_voltage:.9f}")

        sweep_type = st.selectbox("Sweep Type", ["Linear", "Logarithmic"])
        voltage_range = st.selectbox("Voltage Range", ["Auto", "Best Fixed", "200mV", "2.0V", "20.0V", "200.0V"])
        current_limit = high_precision_input("Current Limit (A)", value=0.0)
        delay_seconds = high_precision_input("Delay Seconds", value=0.1)

    # Voltage List Sweep mode (only CSV import)
    elif source_mode == "Voltage List Sweep":
        stepper = st.checkbox('Stepper')
        st.write("Please import a CSV file for the voltage list sweep:")
        st.file_uploader("Import File", type=["csv"])
        voltage_range = st.selectbox("Voltage Range", ["Auto", "Best Fixed", "200mV", "2.0V", "20.0V", "200.0V"])
        current_limit = high_precision_input("Current Limit (A)", value=0.0)
        delay_seconds = high_precision_input("Delay Seconds", value=0.1)

    # Current Bias mode (same as Voltage Bias but for current)
    elif source_mode == "Current Bias":
        current_level = high_precision_input("Current Level (A)", value=0.0)
        current_range = st.selectbox("Current Range", [
            "Auto", "Best Fixed", "1nA", "10nA", "100nA", "1μA", "10μA", 
            "100μA", "1mA", "10mA", "100mA", "1A", "1.55A"
        ])
        voltage_limit = high_precision_input("Voltage Limit (V)", value=0.0)
        num_measurements = integer_input("Number of Measurements", value=10)
        delay_seconds = high_precision_input("Delay Seconds", value=0.1)

    # Current Sweep mode (same logic as Voltage Sweep but for current)
    elif source_mode == "Current Sweep":
        stepper = st.checkbox('Stepper')
        dual_sweep = st.checkbox('Dual Sweep')
        start_current = high_precision_input("Start Current (A)", value=0.0)
        stop_current = high_precision_input("Stop Current (A)", value=5.0)
        
        st.subheader("Choose Step Current or Number of Steps")
        step_type = st.radio("Input Type", ["Step Current", "Number of Steps"])

        if step_type == "Step Current":
            step_current = high_precision_input("Step Current (A)", value=0.05)
            num_steps = int((stop_current - start_current) / step_current) + 1
            st.write(f"Number of Steps: {num_steps}")
        else:
            num_steps = integer_input("Number of Steps", value=100)
            step_current = (stop_current - start_current) / (num_steps - 1)
            st.write(f"Step Current: {step_current:.9f}")

        sweep_type = st.selectbox("Sweep Type", ["Linear", "Logarithmic"])
        current_range = st.selectbox("Current Range", [
            "Auto", "Best Fixed", "1nA", "10nA", "100nA", "1μA", "10μA", 
            "100μA", "1mA", "10mA", "100mA", "1A", "1.55A"
        ])
        voltage_limit = high_precision_input("Voltage Limit (V)", value=0.0)
        delay_seconds = high_precision_input("Delay Seconds", value=0.1)

    # Current List Sweep mode (only CSV import)
    elif source_mode == "Current List Sweep":
        stepper = st.checkbox('Stepper')
        st.write("Please import a CSV file for the current list sweep:")
        st.file_uploader("Import File", type=["csv"])
        current_range = st.selectbox("Current Range", [
            "Auto", "Best Fixed", "1nA", "10nA", "100nA", "1μA", "10μA", 
            "100μA", "1mA", "10mA", "100mA", "1A", "1.55A"
        ])
        voltage_limit = high_precision_input("Voltage Limit (V)", value=0.0)
        delay_seconds = high_precision_input("Delay Seconds", value=0.1)

    # Add "Run Measurement" Button
    if st.button("Run Measurement"):
        st.session_state['run_measurement'] = True
        st.session_state['data'] = []  # Initialize data storage
    #real_time_data_update()


with col2:
    st.subheader('Measurement Settings')

    if source_mode in ['Voltage Bias', 'Voltage Sweep', 'Voltage List Sweep']:
        # Measure Current section
        st.text('Measure Current:')
        enable_measure_current = st.checkbox('Enable Measure Current', value=True)
        if enable_measure_current:
            current_range = st.selectbox('Range:', ['Auto', 'Best Fixed', '1nA', '10nA', '100nA', '1μA', '10μA', '100μA', '1mA', '10mA', '100mA', '1.0A'])
            if current_range == 'Auto':
                min_auto_range = st.selectbox('Min Auto Range:', ['1nA', '10nA', '100nA', '1μA', '10μA', '100μA', '1mA', '10mA', '100mA'])

        # Measure Voltage section
        st.text('Measure Voltage:')
        enable_measure_voltage = st.checkbox('Enable Measure Voltage', value=True)
        if enable_measure_voltage:
            voltage_type = st.selectbox('Type:', ['Programmed', 'Measured'])

    elif source_mode in ['Current Bias', 'Current Sweep', 'Current List Sweep']:
        # Measure Voltage section
        st.text('Measure Voltage:')
        enable_measure_voltage = st.checkbox('Enable Measure Voltage', value=True)
        if enable_measure_voltage:
            voltage_range = st.selectbox('Range:', ['Auto', 'Best Fixed', '20mV', '200mV', '2.0V', '20.0V', '200.0V'])
            if voltage_range == 'Auto':
                min_volt_range = st.selectbox('Min Auto Range:', ['20mV', '200mV', '2.0V', '20.0V'])

        # Measure Current section
        st.text('Measure Current:')
        enable_measure_current = st.checkbox('Enable Measure Current', value=True)
        if enable_measure_current:
            current_type = st.selectbox('Type:', ['Programmed', 'Measured'])

    # Common measurement settings for all modes
    st.text('Measure Resistance:')
    enable_measure_resistance = st.checkbox('Enable Measure Resistance', value=True)
    if enable_measure_resistance:
        resistance_range = st.selectbox('Range:', ['Auto', 'Other Options TBD'])
        if resistance_range == 'Auto':
            min_resistance_range = st.selectbox('Min Auto Range:', ['20Ω', 'Other Options TBD'])

    enable_timestamp = st.checkbox('Enable Timestamp')
    enable_measure_power = st.checkbox('Enable Measure Power')

    # Measurement Speed Settings
    st.subheader('Measurement Speed Settings')
    nplc = high_precision_input('NPLC', 1.0)
    auto_zero = st.selectbox('Auto Zero:', ['On', 'Off'])

    # Advanced Configuration as a dropdown
    with st.expander('Advanced Configuration'):
        input_jacks = st.selectbox('Input Jacks:', ['Front', 'Rear'])
        sensing_mode = st.selectbox('Sensing Mode:', ['2-Wire', '4-Wire'])
        output_off_state = st.selectbox('Output OFF State:', ['Normal', 'High-Z', 'Zero', 'Guard'])
        high_capacitance = st.selectbox('High Capacitance:', ['Off', 'On'])
        offset_compensated_ohms = st.selectbox('Offset Compensated Ohms:', ['Off', 'On'])

# Tab 2: Sheet (Placeholder)
with tab2:
    st.header("Real-Time Data (Sheet)")

    # Initialize data sheet columns based on enabled measurement settings
    data_columns = []

    # Add columns if corresponding settings are enabled
    if enable_measure_current:
        data_columns.append("Current (A)")
    if enable_measure_voltage:
        data_columns.append("Voltage (V)")
    if enable_measure_resistance:
        data_columns.append("Resistance (Ω)")
    if enable_timestamp:
        data_columns.append("Timestamp (s)")
    if enable_measure_power:
        data_columns.append("Power (W)")

    # Placeholder for the data values (replace with actual measurements as you gather data)
    data_values = {column: [] for column in data_columns}

    # Display the table with selected columns
    if data_columns:
        st.write("### Data Sheet")
        st.table(data_values)  # Displays an empty table initially with chosen columns
    else:
        st.write("No measurements selected for display in the data sheet.")


# Tab 3: Graph 
with tab3:

    with st.container():
        col1, col2 = st.columns([1, 3])

    # Left Column: Axis and Options Selection
    with col1:
        st.header("Graph Settings")

        # X-Axis Selection
        st.subheader("X-Axis")
        x_axis_options = []
        if enable_measure_voltage:
            x_axis_options.append("Smu1.V")
        if enable_measure_current:
            x_axis_options.append("Smu1.I")
        if enable_measure_resistance:
            x_axis_options.append("Smu1.R")
        if enable_timestamp:
            x_axis_options.append("Smu1.Time")
        if enable_measure_power:
            x_axis_options.append("Smu1.Power")
        selected_x_axis = st.selectbox("Select X-Axis Measurement", x_axis_options)

        # Y1-Axis Selection
        st.subheader("Y1-Axis")
        selected_y1_axis = st.selectbox("Select Y1-Axis Measurement", x_axis_options)

        # Y2-Axis Selection
        st.subheader("Y2-Axis")
        selected_y2_axis = st.selectbox("Select Y2-Axis Measurement", x_axis_options)

        # Options for Scaling
        st.subheader("Options")
        scale_type = st.radio("Scale Type", ["Auto Scale", "Manual Scale"])

        # Manual Scale Options
        if scale_type == "Manual Scale":
            def high_precision_manual_input(label, value=0.0, key=None, format_str="%.12f"):
            # Input field for user entry
                input_value = st.text_input(label, value=f"{value:.12f}".rstrip('0').rstrip('.'), key=key)
                try:
                    input_value = float(input_value)
                    return input_value
                except ValueError:
                    st.error("Please enter a valid number")
                    return value
            
            st.write("X-Axis Scale")
            x_min = high_precision_manual_input("Min:", 0.0, key="x_min")
            x_max = high_precision_manual_input("Max:", 0.0, key="x_max")

            st.write("Y1-Axis Scale")
            y1_min = high_precision_manual_input("Min:", 0.0, key="y1_min")
            y1_max = high_precision_manual_input("Max:", 0.0, key="y1_max")

            st.write("Y2-Axis Scale")
            y2_min = high_precision_manual_input("Min:", 0.0, key="y2_min")
            y2_max = high_precision_manual_input("Max:", 0.0, key="y2_max")

    # Right Column: Graph Display
    with col2:
        st.header("Real-Time Graph")

        # Sample data for plotting (replace with actual data)
        import numpy as np
        x_data = np.linspace(1e-12, 4e-3, 100)
        y1_data = np.sin(x_data * 1e6)
        y2_data = np.cos(x_data * 1e6)

        # Plotting the graph
        fig, ax1 = plt.subplots()

        # Plotting selected data on Y1-Axis
        ax1.plot(x_data, y1_data, label=selected_y1_axis, color="blue")
        ax1.set_xlabel(selected_x_axis)
        ax1.set_ylabel(selected_y1_axis, color="blue")

        # If Y2-Axis is different, plot it as a second y-axis
        if selected_y1_axis != selected_y2_axis:
            ax2 = ax1.twinx()
            ax2.plot(x_data, y2_data, label=selected_y2_axis, color="red")
            ax2.set_ylabel(selected_y2_axis, color="red")

        # Applying manual scaling if enabled
        if scale_type == "Manual Scale":
            ax1.set_xlim(float(x_min), float(x_max))
            ax1.set_ylim(float(y1_min), float(y1_max))
            if selected_y1_axis != selected_y2_axis:
                ax2.set_ylim(float(y2_min), float(y2_max))

        # Display the plot
        st.pyplot(fig)
