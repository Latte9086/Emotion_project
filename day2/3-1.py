import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('./day1/2-2.csv')
df.columns = df.columns.str.strip()

df["AU12_diff"] = df["AU12_r"].diff()

plt.plot(df['timestamp'], df['AU12_diff'])
plt.legend()
plt.xlabel('Time[s]')
plt.ylabel('AU Intensity')
plt.show()