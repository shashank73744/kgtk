The cat command combines (concatenates) KGTK files, optionally decompressing
input files and compressing the output file, while managing the KGTK column
headers appropriately. This differs from the zconcat command, which
decompresses and concatenates files without managing their KGTK headers.

Input and output files may be (de)compressed using a algorithm selected
by the file extension: .bz2 .gz .lz4 .xy

When merging the column headers, KGTK's required column aliases are respected,
with the leftmost alias seen taking priority.  For example, if the first
input file has a "node1" column and the second has a "from" column, the two
columns will be combined as the "node1" column in the output file.

Normally, the files being combined must be either all KGTK edge files or all
KGTK node files, but that constraint can be overridden with --mode=NONE.

Optionally, the output can be written in a selection of other formats.

## Usage

```bash
usage: kgtk cat [-h] [-i INPUT_FILE [INPUT_FILE ...]] [-o OUTPUT_FILE]
                [--output-format {csv,json,json-map,json-map-compact,jsonl,jsonl-map,jsonl-map-compact,kgtk,md,tsv,tsv-csvlike,tsv-unquoted,tsv-unquoted-ep}]
                [-v [optional True|False]]

Concatenate two or more KGTK files, merging the columns appropriately. All files must be KGTK edge files or all files must be KGTK node files (unless overridden with --mode=NONE). 

Additional options are shown in expert help.
kgtk --expert cat --help

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT_FILE [INPUT_FILE ...], --input-files INPUT_FILE [INPUT_FILE ...]
                        KGTK input files (May be omitted or '-' for stdin.)
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        The KGTK output file. (May be omitted or '-' for
                        stdout.)
  --output-format {csv,json,json-map,json-map-compact,jsonl,jsonl-map,jsonl-map-compact,kgtk,md,tsv,tsv-csvlike,tsv-unquoted,tsv-unquoted-ep}
                        The file format (default=kgtk)

  -v [optional True|False], --verbose [optional True|False]
                        Print additional progress messages (default=False).usage: kgtk cat [-h] [-i INPUT_FILE [INPUT_FILE ...]] [-o OUTPUT_FILE]
                [--output-format {csv,json,json-map,json-map-compact,jsonl,jsonl-map,jsonl-map-compact,kgtk,md,tsv,tsv-csvlike,tsv-unquoted,tsv-unquoted-ep}]
                [-v [optional True|False]]

Concatenate two or more KGTK files, merging the columns appropriately. All files must be KGTK edge files or all files must be KGTK node files (unless overridden with --mode=NONE). 

Additional options are shown in expert help.
kgtk --expert cat --help

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT_FILE [INPUT_FILE ...], --input-files INPUT_FILE [INPUT_FILE ...]
                        KGTK input files (May be omitted or '-' for stdin.)
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        The KGTK output file. (May be omitted or '-' for
                        stdout.)
  --output-format {csv,json,json-map,json-map-compact,jsonl,jsonl-map,jsonl-map-compact,kgtk,md,tsv,tsv-csvlike,tsv-unquoted,tsv-unquoted-ep}
                        The file format (default=kgtk)

  -v [optional True|False], --verbose [optional True|False]
                        Print additional progress messages (default=False).```

## Output Formats

| Format | Extension | Description |
| ------ | --------- | ----------- |
| kgtk   | (default) | KGTK tab separated values file. |
| csv    | .csv      | A simple comma separated value file with doubled quoting and column headers. |
| md	 | .md       | GitHub markdown tables. |
| json   | .json     | JSON list of lists of strings with column header line. |
| json-map | (none)  | JSON list of maps from column names to string values. |
| json-map-compact | (none)  | JSON list of maps from column names to string values with empty values suppressed. |
| jsonl  | .jsonl    | JSON lines of lists of strings  with column header line. |
| jsonl-map | (none)  | JSON lines of maps from column names to string values. |
| jsonl-map-compact | (none)  | JSON lines of maps from column names to string values with empty values suppressed. |
| tsv | (none) | Tab separated values.  Dates have their sigils removed, and strings have the backslash escape removed before pipes. |
| tsv-csvlike | (none) | Tab separated values.  Dates have their sigils removed, and strings are transformed into CSV-like double quoted strings, losing the language code if present. |
| tsv-unquoted | (none) | Tab separated values.  Dates have their sigils removed, and strings have their content exposed without quotes and without escapes before pipes. |
| tsv-unquoted-ep | (none) | Tab separated values.  Dates have their sigils removed, and strings have their content exposed without quotes ; pipes retain their preceeding escapes. |

## Examples

Combine two or more KGTK files, sending the output to standard output.

```bash
kgtk cat -i file1.tsv file2.tsv
```

Combine two gzipped KGTK files, sending the output to a bzip2 file.

```bash
kgtk cat -i file1.tsv.gz file2.tsv.gz -o ofile.tsv.bz2
```

Suppose that `file1.tsv` contains the following table in KGTK format:

| id  | node1      | label       | node2                 | rank |
|-----|------------|-------------|-----------------------|------|
| t1  | terminator | label       | The Terminator@en     | 4    |
| t2  | terminator | instance_of | film                  | 3    |
| t3  | terminator | genre       | action                | 1    |
| t9  | terminator | director    | james_cameron         | 8    |
| t10 | terminator | cast        | arnold_schwarzenegger | 2    |
| t11 | t10        | role        | terminator            | 7    |
| t12 | terminator | cast        | michael_biehn         | 2    |
| t13 | t12        | role        | kyle_reese            | 1    |
| t14 | terminator | cast        | linda_hamilton        | 2    |
| t15 | t14        | role        | sarah_connor          | 9    |


and `file2.tsv` contains the following table in KGTK format:

| id  | node1                 | label      | node2                    | language |
|-----|-----------------------|------------|--------------------------|----------|
| h1  | james_cameron         | label      | James Cameron            | en       |
| h3  | james_cameron         | birth_date | ^1954-08-16T00:00:00Z/11 |          |
| h5  | arnold_schwarzenegger | label      | Arnold Schwarzenegger    | en       |
| h7  | arnold_schwarzenegger | birth_date | ^1947-07-30T00:00:00Z/11 |          |
| h9  | michael_biehn         | label      | Michael Biehn            | en       |
| h11 | michael_biehn         | birth_date | ^1956-07-31T00:00:00Z/11 |          |
| h13 | linda_hamilton        | label      | Linda Hamilton           | en       |
| h15 | linda_hamilton        | birth_date | ^1956-09-26T00:00:00Z/11 |          |

The result will be the following table in KGTK format:

| id  | node1                 | label       | node2                    | rank | language |
|-----|-----------------------|-------------|--------------------------|------|----------|
| t1  | terminator            | label       | The Terminator@en        | 4    |          |
| t2  | terminator            | instance_of | film                     | 3    |          |
| t3  | terminator            | genre       | action                   | 1    |          |
| t9  | terminator            | director    | james_cameron            | 8    |          |
| t10 | terminator            | cast        | arnold_schwarzenegger    | 2    |          |
| t11 | t10                   | role        | terminator               | 7    |          |
| t12 | terminator            | cast        | michael_biehn            | 2    |          |
| t13 | t12                   | role        | kyle_reese               | 1    |          |
| t14 | terminator            | cast        | linda_hamilton           | 2    |          |
| t15 | t14                   | role        | sarah_connor             | 9    |          |
| h1  | james_cameron         | label       | James Cameron            |      | en       |
| h3  | james_cameron         | birth_date  | ^1954-08-16T00:00:00Z/11 |      |          |
| h5  | arnold_schwarzenegger | label       | Arnold Schwarzenegger    |      | en       |
| h7  | arnold_schwarzenegger | birth_date  | ^1947-07-30T00:00:00Z/11 |      |          |
| h9  | michael_biehn         | label       | Michael Biehn            |      | en       |
| h11 | michael_biehn         | birth_date  | ^1956-07-31T00:00:00Z/11 |      |          |
| h13 | linda_hamilton        | label       | Linda Hamilton           |      | en       |
| h15 | linda_hamilton        | birth_date  | ^1956-09-26T00:00:00Z/11 |      |          |

Suppose that `file3.tsv` contains the following data **not** in KGTK format,

| a   | b              | c           | d                         |
|-----|----------------|-------------|---------------------------|
| h21 | robert_patrick | label       | Robert Patrick            |
| h22 | robert_patrick | instance_of | human                     |
| h23 | robert_patrick | birth_date  | ^1958-11-05T00:00:00Z/11  |
| h24 | robert_patrick | country     | United States of America |

trying to run the command ,

```
kgtk cat -i file1.tsv.gz file3.tsv 
```

will result in an error message ,

```
In input 2 header 'a	b	c	d': Missing required column: id | ID
Exit requested
```

We can force `kgtk cat` command to concatenate anyway using the `--mode NONE` option,

```
kgtk cat -i file1.tsv.gz file3.tsv --mode NONE
```

| id  | node1      | label       | node2                 | rank | a   | b              | c           | d                        |
|-----|------------|-------------|-----------------------|------|-----|----------------|-------------|--------------------------|
| t1  | terminator | label       | The Terminator@en     | 4    |     |                |             |                          |
| t2  | terminator | instance_of | film                  | 3    |     |                |             |                          |
| t3  | terminator | genre       | action                | 1    |     |                |             |                          |
| t9  | terminator | director    | james_cameron         | 8    |     |                |             |                          |
| t10 | terminator | cast        | arnold_schwarzenegger | 2    |     |                |             |                          |
| t11 | t10        | role        | terminator            | 7    |     |                |             |                          |
| t12 | terminator | cast        | michael_biehn         | 2    |     |                |             |                          |
| t13 | t12        | role        | kyle_reese            | 1    |     |                |             |                          |
| t14 | terminator | cast        | linda_hamilton        | 2    |     |                |             |                          |
| t15 | t14        | role        | sarah_connor          | 9    |     |                |             |                          |
|     |            |             |                       |      | h21 | robert_patrick | label       | Robert Patrick           |
|     |            |             |                       |      | h22 | robert_patrick | instance_of | human                    |
|     |            |             |                       |      | h23 | robert_patrick | birth_date  | ^1958-11-05T00:00:00Z/11 |
|     |            |             |                       |      | h24 | robert_patrick | country     | United States of America |

# Expert Topic: Adding Column Names

Suppose that you have a TSV (tab-separated values) data file
that looks like a KGTK data file but without the header line.
You can supply a header line with --force-column-names.
You can also use this option when concatenating several
data files, so long as they are all missing header lines and
they should all have the same header line.

For example, assuming that your file(s) are edge files with
the three required columns:

```bash
kgtk cat -i file1.tsv.gz --force-column-names node1 label node2
```
# Expert Topic: Renaming Column Names

There is a special KGTK command, `kgtk rename_columns`, for renaming columns.
However, you may want to rename columns while also using other features of
the `kgtk cat` command, such as combining multiple input files or sampling
data lines.

You have two main choices: override the column names on input, or rename the
column names on output.

Overriding the column names on input can be done by skipping the existing
header record and supplying a replacement list of column names.

```bash
kgtk cat -i file1.tsv.gz --skip-header-record --force-column-names node1 label node2
```

Renaming the column names on output can by done two ways.  First, you can name
all of the new column names using --output-columns.

```bash
kgtk cat -i file1.tsv.gz --output-columns node1 label node2
```

Second, you can rename individual columns using --old-columns and --new-columns.

For example, suppose your input file contained the following table in KGTK format:

| origin | label    | destination      | years |
| ----- | -------- | ---------- | ----- |
| t1  | terminator | label       | The Terminator@en     | 4    |
| t2  | terminator | instance_of | film                  | 3    |

You want to rename the `origin` column to `node1`, and the `destination`
column to `node2`.

```bash
kgtk cat -i file1.tsv.gz --old-columns origin destination --new-columns node1 node2
```

The result will be the following table in KGTK format:

| node1 | label    | node2      | years |
| ----- | -------- | ---------- | ----- |
| t1  | terminator | label       | The Terminator@en     | 4    |
| t2  | terminator | instance_of | film                  | 3    |

When you rename columns on input, the change applies to all input files: they
all must have the same column layout, for which you will provide a new set of
column names. Renaming column names on output can be done when you combine a
disparate set of KGTK files.  The rename applies to the merged set of column
names computed by `kgtk cat`.

# Expert Topic: Data Sampling

Limit the number of records read (like `head`).

```bash
kgtk cat -i file1.tsv.gz --record-limit 4
```

The result will be the following table in KGTK format:

| id | node1      | label       | node2             | rank |
|----|------------|-------------|-------------------|------|
| t1 | terminator | label       | The Terminator@en | 4    |
| t2 | terminator | instance_of | film              | 3    |
| t3 | terminator | genre       | action            | 1    |
| t9 | terminator | director    | james_cameron     | 8    |

Skip some number of initial records, then begin processing.

```bash
kgtk cat -i file1.tsv.gz --initial-skip-count 4
```

The result will be the following table in KGTK format:

| id  | node1      | label | node2                 | rank |
|-----|------------|-------|-----------------------|------|
| t10 | terminator | cast  | arnold_schwarzenegger | 2    |
| t11 | t10        | role  | terminator            | 7    |
| t12 | terminator | cast  | michael_biehn         | 2    |
| t13 | t12        | role  | kyle_reese            | 1    |
| t14 | terminator | cast  | linda_hamilton        | 2    |
| t15 | t14        | role  | sarah_connor          | 9    |

Process the last n records relative to the end (like `tail`).
You must know the number of data records in the file (the number of lines
in the file minus the header line).

```bash
kgtk cat -i file1.tsv.gz --record-limit 6 --tail-count 3
```

The result will be the following table in KGTK format:

| id  | node1      | label    | node2                 | rank |
|-----|------------|----------|-----------------------|------|
| t9  | terminator | director | james_cameron         | 8    |
| t10 | terminator | cast     | arnold_schwarzenegger | 2    |
| t11 | t10        | role     | terminator            | 7    |

Process every nth record (after skipping, but calculated relative to
the count of data lines read before skipping).  The following example will
process every second line.

```bash
kgtk cat -i file1.tsv.gz --every-nth-record 2
```

The result will be the following table in KGTK format:

| id  | node1      | label       | node2         | rank |
|-----|------------|-------------|---------------|------|
| t2  | terminator | instance_of | film          | 3    |
| t9  | terminator | director    | james_cameron | 8    |
| t11 | t10        | role        | terminator    | 7    |
| t13 | t12        | role        | kyle_reese    | 1    |
| t15 | t14        | role        | sarah_connor  | 9    |

If both --initial-skip-count # and --record-limit # --tail-count #
are specified, the number of records skipped will be the maximum of
the initial skip count and (record limit minus tail count).

# Expert Topic: Output Formats

Althouth `kgtk cat` is primarilly intended to read and write KGTK format
files, it can also be used to convert KGTK files to a number of other formats.

| Format | Description |
| ------ | ----------- |
| csv    | comma-separated values. |
| json   | A JSON list of lists. The first inner list contains the column names, the remaining inner lists contain data rows. |
| json-map | A JSON list of maps. Column names are mapped to data values. |
| json-map-compact | A JSON list of maps. Column names are mapped to data values, whith empty data values omitted. |
| jsonl   | A JSON Lines file od lists. The first inner list contains the column names, the remaining inner lists contain data rows. |
| jsonl-map | A JSON Lines file of maps. Column names are mapped to data values. |
| jsonl-map-compact | A JSON Lines file of maps. Column names are mapped to data values, whith empty data values omitted. |
| kgtk | KGTK tab-separated value format. |
| md | GitHub Markdown tables |

The csv and json* formats use very primitive conversions at the present time,
which do not provide proper treatment for different data types: booleans,
numbers, strings.
