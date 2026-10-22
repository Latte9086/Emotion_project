import pandas as pd

df = pd.read_csv('A.csv')

print("指定された列のデータを表示します:")
df.columns = df.columns.str.strip()
columns_to_show = ['frame', 'timestamp', 'confidence', 'pose_Rx', 'pose_Ry', 'pose_Rz']
print(df[columns_to_show].head())