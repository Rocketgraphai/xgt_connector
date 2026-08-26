class MyDict(dict):
    
    """
    def __getattr__(self, name):
        print(f"_getattr_ called for: {name}")
        return super().__getattribute__(name)
    
    def __init__(self, *args, **kwargs):
        print("INIT CALLED")
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        print(f"GETITEM: {key}")
        return super().__getitem__(key)

    def keys(self):
        print("KEYS CALLED")
        return super().keys()
    """

import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import ast
import polars as pl

class MyDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.derived = self._compute_derived()

    def _compute_derived(self):
        return list(self.keys())  # or whatever logic

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.derived = self._compute_derived()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.derived = self._compute_derived()

    def __setstate__(self, state):
        self.update(state)
        self.derived = self._compute_derived()

class MyCustom():
    def __init__(self, *args, **kwargs):
        self.derived = 10

df = pd.DataFrame([
    MyDict(id=1, a=10, b=20),
    MyDict(id=2, a=20, b=30)
])

df1 = pd.DataFrame([
    MyCustom(),
    MyCustom()
])

print( MyDict(id=1, a=10, b=20))
print(df)
print(df1)
df.to_csv('output.csv', index=False)
print(pd.read_csv('output.csv'))

#df1.to_parquet('output.parquet', index=False)
#table = pa.Table.from_pandas(df1)


df = pd.DataFrame({'col': [MyDict(id=0, a=10, b=20, c={'l': 10, 'l2': 20}), MyDict(id=2, a=20, b=30)],'col1': [MyDict(id=0, c=10, d=20), MyDict(id=2, c=20, d=30)] })
df.to_csv('output.csv', index=False)
print(type(pd.read_csv('output.csv')['col'][0]))
df_csv = pd.read_csv('output.csv')
df_csv["col"] = df_csv["col"].apply(ast.literal_eval)
print(df_csv['col'][0]['c']['l'])
#df['col'] = df['col'].map(lambda x: ast.literal_eval(x))

exit(0)
df.to_parquet('output.parquet', index=False)
table = pa.Table.from_pandas(df)
pdf = pl.from_arrow(table)
with open("output1.csv", "wb") as f:
    pacsv.write_csv(table.flatten(), f)
pq.write_table(table, 'output1.parquet')
print(df)
print(table)
print(table.to_pandas())

expanded = df['col'].apply(pd.Series)
df2 = pd.concat([df.drop(columns='col'), expanded], axis=1)
print(df2)

print(pd.read_csv('output.csv'))
print(pd.read_parquet('output.parquet'))
print(pd.read_parquet('output1.parquet'))

df = pd.read_csv('output.csv')
df['data'] = df['col'].map(lambda x: MyDict(ast.literal_eval(x)))
df['data'].map(lambda x: print(x.derived))
print(df)
table = pacsv.read_csv("output.csv")
print(table)
print("------")
print(pdf)
#pdf.write_csv("output3.csv")
pdf.write_parquet("output3.parquet", compression="zstd")
pdf = pl.read_parquet("output.parquet")
rows = pdf.to_dict(as_series=False)
print(pdf)
print(rows)

