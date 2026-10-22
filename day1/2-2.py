import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('2-2.csv')
df.columns = df.columns.str.strip()

plt.plot(df['timestamp'], df['AU06_r'], label='AU06')
plt.plot(df['timestamp'], df['AU12_r'], label='AU12')
plt.plot(df['timestamp'], df['AU04_r'], label='AU04')

plt.legend()
plt.xlabel('Time[s]')
plt.ylabel('AU Intensity')
plt.show()