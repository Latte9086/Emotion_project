import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('./day1/2-2.csv')
df.columns = df.columns.str.strip()

df["smileFlag"] = (df["AU12_r"] > 2).astype(int)

df["AU_smooth"] = (
    df["AU12_r"]
    .rolling(window=8, center=True)
    .mean()
)

plt.plot(df['timestamp'], df["AU12_r"])
plt.plot(df['timestamp'], df["AU_smooth"])
plt.legend()
plt.xlabel('Time[s]')   
plt.ylabel('AU Intensity')
plt.show()