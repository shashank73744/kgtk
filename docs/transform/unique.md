The `kgtk unique` command reads a KGTK file, constructing a second KGTK file
containing the unique values found in one of the columns of the input file.  Each unique
value may be accompanied by an occurence count, depending on the format
selected for the output file.

In the default output format, the output file is a KGTK edge file.
The `node1` column contains the unique values, the `label` column value is `count`,
and the `node2` column contains the unique count.

Since KGTK edge files cannot have an empty `node1` column, the `--empty EMPTY_VALUE`
option provides a substitute value (e.g. NONE) that will be used in the ouput
KGTK file to represent empty values in the input KGTK file.  When the empty
value is itself empty, (the default) empty values in the input file will not
be included in the output file.

The `--column COLUMN_NAME` option specifies the name of the column to
count unique values.  If not specified, the default is the `node2` column or its alias.

The value used in the `label` column of the output file, normally `count`, may be changed
with the `--label LABEL_VALUE` option.

The `--prefix PREFIX` option supplies a prefix to the unique values in the output file.

The `--format xxx` option selects an output format:

Format                 | Description
---------------------- | -----------
`--format edge`        | This format creates a KGTK edge file. The `node1` column contains the unique values, the `label` column value is `count` (which may be changed with `--label LABEL_VALUE`), and the `node2` column contains the unique count. This is the default output format.
`--format node`        | This format creates a KGTK node file.  The value (prefixed if requested) appears in the `id` column of the output file, and new columns (prefixed) are created for each unique value found in the specified column in the input file.
`--format node-counts` | This format creates a KGTK node file with two columns.  The `id` column will contain the (optionally prefixed) unique values, while the second column, named `count`, unless changed by `--label LABEL_VALUE`, will contain the count.
`--format node-only`   | This creates a KGTK node file with a single column, the `id` column, containing the unique values.  The counts are computed but not written.

Using the `--where WHERE_COLUMN_NAME` and `--in WHERE_VALUES...` options, you can restrict the count to records where the value in a specified column matches a list of specified values.  More sophisticated filtering can be obtained by running `kgtk filter` to provide the input to `kgtk unique`.

`kgtk unique` normally builds an in-memory dictionary of the unique
values and counts.  Performance will be poor, and execution may fail, if there
are a very large number of unique values, causing main memory to be exhausted.
If you run out of main memory, you should presort the input file and use
`kgtk unique --presorted` to avoid  building the in-memory dictionary.

## Usage

```
usage: kgtk unique [-h] [-i INPUT_FILE] [-o OUTPUT_FILE] --column COLUMN_NAME [--empty EMPTY_VALUE]
                   [--label LABEL_VALUE] [--format {edge,node,node-counts,node-only}] [--prefix PREFIX]
                   [--where WHERE_COLUMN_NAME] [--in WHERE_VALUES [WHERE_VALUES ...]] [--presorted [True|False]]
                   [-v [optional True|False]]

Count the unique values in a column in a KGTK file. Write the unique values and counts as a new KGTK file.

Additional options are shown in expert help.
kgtk --expert unique --help

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input-file INPUT_FILE
                        The KGTK input file. (May be omitted or '-' for stdin.)
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        The KGTK output file. (May be omitted or '-' for stdout.)
  --column COLUMN_NAME  The column to count unique values (default=node2 or its alias).
  --empty EMPTY_VALUE   A value to substitute for empty values (default=).
  --label LABEL_VALUE   The output file label column value (default=count).
  --format {edge,node,node-counts,node-only}
                        The output file format and mode (default=edge).
  --prefix PREFIX       The value prefix (default=).
  --where WHERE_COLUMN_NAME
                        The name of a column for a record selection test. (default=None).
  --in WHERE_VALUES [WHERE_VALUES ...]
                        The list of values for a record selection test. (default=None).
  --presorted [True|False]
                        When True, the input file is presorted. (default=False).

  -v [optional True|False], --verbose [optional True|False]
                        Print additional progress messages (default=False).
```

## Examples

Suppose that `file1.tsv` contains the following table in KGTK format:

| node1 | label   | node2 | location | years |
| ----- | ------- | ----- | -------- | ----- |
| eric  | zipcode | 12040 | work     | 5     |
| john  | zipcode | 12345 | home     | 10    |
| john  | zipcode | 12346 |          |       |
| john  | zipcode | 12347 |          |       |
| peter | zipcode | 12040 | home     |       |
| peter | zipcode | 12040 | work     | 6     |
| steve | zipcode | 45600 |          | 3     |
| steve | zipcode | 45601 | work     |       |


Count the unique values in the `location` column:

```bash
kgtk unique -i file1.tsv --column location

```

| node1 | label | node2 |
| ----- | ----- | ----- |
| home  | count | 2     |
| work  | count | 3     |

Count the unique values in the `location` column, using
the value `NONE` for empty values:

```bash
kgtk unique -i file1.tsv --column location --empty NONE

```

| node1 | label | node2 |
| ----- | ----- | ----- |
| NONE  | count | 3     |
| home  | count | 2     |
| work  | count | 3     |

Count the unique values in the `location` column, using
the value `NONE` for empty values, but use the `node` format
for the output file:

```bash
kgtk unique -i file1.tsv --column location --empty NONE --format node

```

| id       | NONE | home | work |
| -------- | ---- | ---- | ---- |
| location | 3    | 2    | 3    |

Give each column name a prefix:

```bash
kgtk unique -i file1.tsv --column location --empty NONE --format node --prefix 'location;'

```

| id       | location;NONE | location;home | location;work |
| -------- | ---- | ---- | ---- |
| location | 3    | 2    | 3    |

Filter the input file and create an edge-stype output file:

```bash
kgtk unique -i file1.tsv --column location --where node1 --in peter
```

| node1 | label | node2 |
| -- | -- | -- |
| home | count | 1 |
| work | count | 1 |
