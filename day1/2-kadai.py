import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('2-2.csv')
df.columns = df.columns.str.strip()

df["happy"] = df["AU25_r"]
df["surprise"] = df["AU01_r"] + df["AU02_r"] + df["AU05_r"] + df["AU26_r"]
df["sadness"] = df["AU04_r"]

plt.plot(df['timestamp'], df['happy'], label='happy')
plt.plot(df['timestamp'], df['surprise'], label='surprise')
plt.plot(df['timestamp'], df['sadness'], label='sadness')

plt.legend()
plt.xlabel('Time[s]')
plt.ylabel('AU Intensity')
plt.show()