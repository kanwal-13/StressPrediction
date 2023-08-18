import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis
from scipy.signal import find_peaks
import joblib
import bluepy.btle as btle

# Initialize buffers and counters
eda_buffer = []
hr_buffer = []
eda_mean_buffer = []
hr_mean_buffer = []

# Define the number of means to keep and the buffer size
num_means_to_keep = 10
buffer_size = 40

# Define columns for the feature DataFrame
eda_cols = ['EDA_Mean', 'EDA_Min', 'EDA_Max', 'EDA_Std', 'EDA_Kurtosis', 'EDA_Skew',
            'EDA_Num_Peaks', 'EDA_Amphitude', 'EDA_Duration']
hr_cols = ['HR_Mean', 'HR_Min', 'HR_Max', 'HR_Std', 'HR_RMS']
mean_buffer_cols = ['Mean_Buffer_' + str(i) for i in range(num_means_to_keep)]
df_features = pd.DataFrame(columns=eda_cols + hr_cols + mean_buffer_cols)

def calculate_eda_features(data):
    # Calculate statistical and shape features for the given EDA data
    eda_min, eda_max, eda_mean, eda_std = np.min(data), np.max(data), np.mean(data), np.std(data)
    eda_skew = np.mean((data - eda_mean)*3) / (eda_std*3)
    eda_kurtosis = np.mean((data - eda_mean)*4) / (eda_std*4)
    
    peaks, properties = find_peaks(data, width=5)
    num_peaks = len(peaks)
    prominences = np.array(properties['prominences'])
    widths = np.array(properties['widths'])
    amphitude = np.sum(prominences)
    duration = np.sum(widths)

    return [eda_mean, eda_min, eda_max, eda_std, eda_kurtosis, eda_skew, num_peaks, amphitude, duration]

def calculate_hr_features(data):
    # Calculate statistical features for the given HR data
    hr_mean, hr_min, hr_max, hr_std = np.mean(data), np.min(data), np.max(data), np.std(data)
    hr_rms = np.sqrt(np.mean(np.square(np.ediff1d(data))))

    return [hr_mean, hr_min, hr_max, hr_std, hr_rms]

# Load the trained model using joblib
model_path = "final_model.joblib"
loaded_model = joblib.load(model_path)

# Update with the MAC address of your Arduino Nano BLE 33
arduino_mac_address = "XX:XX:XX:XX:XX:XX"

# Initialize BLE connection to Arduino Nano
arduino_peripheral = btle.Peripheral(arduino_mac_address)

# Initialize HR characteristic
hr_uuid = btle.UUID(0x2A37)
hr_char = arduino_peripheral.getCharacteristics(uuid=hr_uuid)[0]

# Start receiving sensor data
while True:
    hr_data = hr_char.read()
    new_hr_value = int.from_bytes(hr_data, byteorder='little', signed=False)

    eda_buffer.append(new_eda_value)
    hr_buffer.append(new_hr_value)

    if len(eda_buffer) == buffer_size:
        eda_mean_buffer.append(np.mean(eda_buffer))
        hr_mean_buffer.append(np.mean(hr_buffer))
        
        eda_buffer = eda_buffer[-buffer_size+20:]
        hr_buffer = hr_buffer[-buffer_size+20:]
        
        if len(eda_mean_buffer) > num_means_to_keep:
            eda_mean_buffer = eda_mean_buffer[-num_means_to_keep:]
            hr_mean_buffer = hr_mean_buffer[-num_means_to_keep:]
        
        if len(eda_mean_buffer) == num_means_to_keep and len(hr_mean_buffer) == num_means_to_keep:
            eda_features = calculate_eda_features(eda_mean_buffer)
            hr_features = calculate_hr_features(hr_mean_buffer)
            
            all_features = eda_features + hr_features + eda_mean_buffer + hr_mean_buffer
            all_features = np.array(all_features)
            
            predicted_class = loaded_model.predict([all_features])
            print("Model's prediction:", predicted_class)
