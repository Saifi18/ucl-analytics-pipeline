## Silver Upload Pattern — Final Working Solution

Decision: asDict(recursive=True) + pd.DataFrame() + pyarrow BytesIO

Root cause: Databricks CE Serverless attaches PlanMetrics to DataFrame
objects at the JVM level. toPandas() and collect() +
createDataFrame() both preserve this internal reference.

Fix: row.asDict(recursive=True) extracts pure Python native types
from each Row with zero Spark object references. pd.DataFrame()
built from plain dicts is fully pyarrow serialisable.

Type preservation: asDict() returns datetime.date, datetime.datetime,
int, bool, str, None — pyarrow maps all of these
natively. No pre-conversion needed.

Lesson: When toPandas() fails with internal Spark errors, always
go through asDict() before Pandas. Severs the JVM entirely.
