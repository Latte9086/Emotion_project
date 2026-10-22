import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('2-2.csv')
df.columns = df.columns.str.strip()

plt.plot(df['timestamp'], df['AU01_r'], label='AU01(Inner Brow Raiser)')
plt.plot(df['timestamp'], df['AU02_r'], label='AU02(Outer Brow Raiser)')
plt.plot(df['timestamp'], df['AU05_r'], label='AU05(Upper Lid Raiser)')
plt.plot(df['timestamp'], df['AU25_r'], label='AU25(Lips Part)')
plt.plot(df['timestamp'], df['AU26_r'], label='AU26(Jaw Drop)')

plt.legend()
plt.xlabel('Time[s]')
plt.ylabel('AU Intensity')
plt.show()