import shutil
import unittest
import tempfile
import shlex
from   io import StringIO
import pandas as pd
from kgtk.cli_entry import cli_entry


# TO DO:
# - file aliasing via --as, realiasing
# - files not required to exist after initial import
# - queries from stdin (query pipes not yet supported)
# - NULL value tests and conversion functions

class TestKGTKQuery(unittest.TestCase):
    def setUp(self) -> None:
        self.file_path = 'data/kypher/graph.tsv'
        self.file_path_gz = 'data/kypher/graph.tsv.gz'
        self.file_path_bz2 = 'data/kypher/graph.tsv.bz2'
        self.quals_path = 'data/kypher/quals.tsv'
        self.works_path = 'data/kypher/works.tsv'
        self.props_path = 'data/kypher/props.tsv'
        self.literals_path = 'data/kypher/literals.tsv'
        self.temp_dir = tempfile.mkdtemp()
        self.sqldb = f'{self.temp_dir}/test.sqlite3.db'
        self.df = pd.read_csv(self.file_path, sep='\t')

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_kgtk_query_default(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 9)

    def test_kgtk_query_default_gzip(self):
        cli_entry("kgtk", "query", "-i", self.file_path_gz, "-o", f'{self.temp_dir}/out.tsv.gz', '--graph-cache',
                  self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv.gz', sep='\t')
        self.assertTrue(len(df) == 9)

    def test_kgtk_query_default_bz2(self):
        cli_entry("kgtk", "query", "-i", self.file_path_bz2, "-o", f'{self.temp_dir}/out.tsv.bz2', '--graph-cache',
                  self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv.bz2', sep='\t')
        self.assertTrue(len(df) == 9)

    def test_kgtk_query_match(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(i)-[:loves]->(c)", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 3)
        ids = list(df['id'].unique())
        self.assertTrue('e11' in ids)
        self.assertTrue('e12' in ids)
        self.assertTrue('e14' in ids)

    def test_kgtk_query_limit(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--limit",
                  "3", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 3)
        ids = list(df['id'].unique())
        self.assertTrue('e11' in ids)
        self.assertTrue('e12' in ids)
        self.assertTrue('e13' in ids)

    def test_kgtk_query_limit_skip(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--limit",
                  "3", "--skip", "2", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 3)
        ids = list(df['id'].unique())
        self.assertTrue('e13' in ids)
        self.assertTrue('e14' in ids)
        self.assertTrue('e21' in ids)

    def test_kgtk_query_hans_filter(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(:Hans)-[]->()", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 2)
        ids = list(df['id'].unique())
        self.assertTrue('e11' in ids)
        self.assertTrue('e21' in ids)

    def test_kgtk_query_otto_name_filter(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(:Otto)-[:name]->()", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 1)
        ids = list(df['id'].unique())
        self.assertTrue('e22' in ids)

    def test_kgtk_query_where_double_letter(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[:name]->(n)", "--where", 'n =~".*(.)\\\\1.*"', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 2)
        ids = list(df['id'].unique())
        self.assertTrue('e22' in ids)
        self.assertTrue('e24' in ids)

    def test_kgtk_query_where_IN(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[:name]->(n)", "--where", 'p IN ["Hans", "Susi"]', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 2)
        ids = list(df['id'].unique())
        self.assertTrue('e21' in ids)
        self.assertTrue('e25' in ids)

    def test_kgtk_query_where_upper_substring(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[:name]->(n)", "--where", "upper(substr(n,2,1)) >= 'J'", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 4)
        ids = list(df['id'].unique())
        self.assertTrue('e22' in ids)
        self.assertTrue('e23' in ids)
        self.assertTrue('e24' in ids)
        self.assertTrue('e25' in ids)

    def test_kgtk_query_where_upper_substring_sorted(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[:name]->(n)", "--where", "upper(substr(n,2,1)) >= 'J'", "--order-by", "substr(n,2,1)",
                  '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 4)
        ids = list(df['id'].unique())
        self.assertTrue('e23' == ids[0])
        self.assertTrue('e24' == ids[1])
        self.assertTrue('e22' == ids[2])
        self.assertTrue('e25' == ids[3])

    def test_kgtk_query_where_upper_substring_sorted_desc(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[:name]->(n)", "--where", "upper(substr(n,2,1)) >= 'J'", "--order-by", "substr(n,2,1) desc",
                  '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 4)
        ids = list(df['id'].unique())
        self.assertTrue('e25' == ids[0])
        self.assertTrue('e22' == ids[1])
        self.assertTrue('e24' == ids[2])
        self.assertTrue('e23' == ids[3])

    def test_kgtk_query_select_columns(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[:name]->(n)", "--where", "upper(substr(n,2,1)) >= 'J'", "--return", "p,n", '--graph-cache',
                  self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 4)
        columns = list(df.columns)
        self.assertTrue('node1' in columns)
        self.assertTrue('node2' in columns)
        node1s = list(df['node1'].unique())
        self.assertTrue('Otto' in node1s)
        self.assertTrue('Joe' in node1s)
        self.assertTrue('Molly' in node1s)
        self.assertTrue('Susi' in node1s)

    def test_kgtk_query_switch_columns(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[r:name]->(n)", "--where", "upper(substr(n,2,1)) >= 'J'", "--return", "p,n, r, r.label",
                  '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 4)
        columns = list(df.columns)
        self.assertTrue('node1' in columns)
        self.assertTrue('node2' in columns)
        self.assertTrue('id' in columns)
        self.assertTrue('label' in columns)
        node1s = list(df['node1'].unique())
        self.assertTrue('Otto' in node1s)
        self.assertTrue('Joe' in node1s)
        self.assertTrue('Molly' in node1s)
        self.assertTrue('Susi' in node1s)

    def test_kgtk_query_return_columns_modify_functions(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[r:name]->(n)", "--where", "upper(substr(n,2,1)) >= 'J'",
                  "--return", "lower(p) as node1, r.label, n, r",
                  '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 4)
        columns = list(df.columns)
        self.assertTrue('node1' in columns)
        self.assertTrue('node2' in columns)
        self.assertTrue('id' in columns)
        self.assertTrue('label' in columns)
        node1s = list(df['node1'].unique())
        self.assertTrue('otto' in node1s)
        self.assertTrue('joe' in node1s)
        self.assertTrue('molly' in node1s)
        self.assertTrue('susi' in node1s)

    def test_kgtk_query_kgtk_unstringify(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[r:name]->(n)", "--where", "upper(substr(n,2,1)) >= 'J'",
                  "--return", "p, r.label, kgtk_unstringify(n) as node2, r",
                  '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 4)
        columns = list(df.columns)
        self.assertTrue('node2' in columns)
        self.assertTrue('node1' in columns)
        self.assertTrue('id' in columns)
        self.assertTrue('label' in columns)
        vals = list(df['node2'].unique())
        self.assertTrue('Molly' in vals)

    def test_kgtk_query_para(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[r:name]->(n)", "--where", " n = $name OR n = $name2 OR n = $name3 ",
                  "--para", "name=\"'Hans'@de\"", "--spara", "name2=Susi", "--lqpara", "name3=Otto@de", '--graph-cache',
                  self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 2)
        columns = list(df.columns)
        self.assertTrue('node2' in columns)
        self.assertTrue('node1' in columns)
        self.assertTrue('id' in columns)
        self.assertTrue('label' in columns)
        ids = list(df['id'].unique())
        self.assertTrue('e25' in ids)
        self.assertTrue('e22' in ids)

    def test_kgtk_query_lgstring_land(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(p)-[r:name]->(n)", "--where", 'n.kgtk_lqstring_lang = "de"', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 2)
        ids = list(df['id'].unique())
        self.assertTrue('e21' in ids)
        self.assertTrue('e22' in ids)

    def test_kgtk_query_reflexive_edges(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(a)-[]->(a)", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 1)
        ids = list(df['id'].unique())
        self.assertTrue('e14' in ids)

    def test_kgtk_query_multi_step_path(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(na)<-[:name]-(a)-[r:loves]->(b)-[:name]->(nb)", "--return", "r, na, r.label, nb", '--graph-cache',
                  self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 3)
        ids = list(df['id'].unique())
        node2s = list(df['node2'].unique())
        node2_1s = list(df['node2.1'].unique())
        self.assertTrue('e14' in ids)
        self.assertTrue('e11' in ids)
        self.assertTrue('e12' in ids)
        self.assertTrue('Joe' in node2s)
        self.assertTrue("'Hans'@de" in node2s)
        self.assertTrue("'Otto'@de" in node2s)
        self.assertTrue('Joe' in node2_1s)
        self.assertTrue('Molly' in node2_1s)
        self.assertTrue('Susi' in node2_1s)

    def test_kgtk_query_multi_step_path_german_lovers(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(na)<-[:name]-(a)-[r:loves]->(b)-[:name]->(nb)",
                  "--where", 'na.kgtk_lqstring_lang = "de" OR nb.kgtk_lqstring_lang = "de"',
                  "--return", "r, na, r.label, nb", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 2)
        ids = list(df['id'].unique())
        node2s = list(df['node2'].unique())
        node2_1s = list(df['node2.1'].unique())
        self.assertTrue('e11' in ids)
        self.assertTrue('e12' in ids)
        self.assertTrue("'Hans'@de" in node2s)
        self.assertTrue("'Otto'@de" in node2s)
        self.assertTrue('Molly' in node2_1s)
        self.assertTrue('Susi' in node2_1s)

    def test_kgtk_query_multi_step_path_german_lovers_anonymous(self):
        cli_entry("kgtk", "query", "-i", self.file_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  # test connection through anonymous node variables instead of a and b:
                  "(na)<-[:name]-()-[r:loves]->()-[:name]->(nb)",
                  "--where", 'na.kgtk_lqstring_lang = "de" OR nb.kgtk_lqstring_lang = "de"',
                  "--return", "r, na, r.label, nb", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 2)
        ids = list(df['id'].unique())
        node2s = list(df['node2'].unique())
        node2_1s = list(df['node2.1'].unique())
        self.assertTrue('e11' in ids)
        self.assertTrue('e12' in ids)
        self.assertTrue("'Hans'@de" in node2s)
        self.assertTrue("'Otto'@de" in node2s)
        self.assertTrue('Molly' in node2_1s)
        self.assertTrue('Susi' in node2_1s)

    def test_kgtk_query__named_multi_graph_join(self):
        cli_entry("kgtk", "query", "-i", self.file_path,
                  "-i", self.works_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "g: (x)-[:loves]->(y), w: (y)-[:works]-(c)", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 3)
        for i, row in df.iterrows():
            if row['id'] == 'e14':
                self.assertEqual(row['node1'], 'Joe')
                self.assertEqual(row['node2'], 'Joe')
                self.assertEqual(row['id.1'], 'w13')
                self.assertEqual(row['node1.1'], 'Joe')
                self.assertEqual(row['label.1'], 'works')
                self.assertEqual(row['node2.1'], 'Kaiser')
                self.assertEqual(row['node1;salary'], 20000)
                self.assertEqual(row['graph'], 'employ')

    def test_kgtk_query_default_multi_graph_join(self):
        cli_entry("kgtk", "query", "-i", self.file_path,
                  "-i", self.works_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(x)-[:loves]->(y), w: (y)-[:works]-(c)", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 3)
        for i, row in df.iterrows():
            if row['id'] == 'e14':
                self.assertEqual(row['node1'], 'Joe')
                self.assertEqual(row['node2'], 'Joe')
                self.assertEqual(row['id.1'], 'w13')
                self.assertEqual(row['node1.1'], 'Joe')
                self.assertEqual(row['label.1'], 'works')
                self.assertEqual(row['node2.1'], 'Kaiser')
                self.assertEqual(row['node1;salary'], 20000)
                self.assertEqual(row['graph'], 'employ')

    def test_kgtk_query_default_multi_graph_join_kgtk_compliant(self):
        cli_entry("kgtk", "query", "-i", self.file_path,
                  "-i", self.works_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "g: (x)-[r:loves]->(y), w: (y)-[:works]-(c)",
                  "--return", 'r, x, r.label, y as node2, c as `node2;work`', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 3)
        for i, row in df.iterrows():
            if row['id'] == 'e11':
                self.assertEqual(row['node1'], 'Hans')
                self.assertEqual(row['node2'], 'Molly')
                self.assertEqual(row['node2;work'], 'Renal')

    def test_kgtk_query_default_multi_graph_join_property_access_restriction_cast_integer(self):
        cli_entry("kgtk", "query", "-i", self.file_path,
                  "-i", self.works_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "g: (x)-[r:loves]->(y), w: (y {salary: s})-[:works]-(c)",
                  "--where", "cast(s, integer) >= 10000",
                  "--return", 'r, x, r.label, y as node2, c as `node2;work`, s as `node2;salary`', '--graph-cache',
                  self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')

        self.assertTrue(len(df) == 2)
        for i, row in df.iterrows():
            if row['id'] == 'e11':
                self.assertEqual(row['node1'], 'Hans')
                self.assertEqual(row['node2'], 'Molly')
                self.assertEqual(row['node2;work'], 'Renal')

    def test_kgtk_query_max(self):
        cli_entry("kgtk", "query", "-i", self.file_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "g: (x)-[r]->(y)",
                  "--return", 'max(x) as node1, r.label, y, r', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 1)
        for i, row in df.iterrows():
            if row['id'] == 'e25':
                self.assertEqual(row['node1'], 'Susi')
                self.assertEqual(row['node2'], 'Susi')

    def test_kgtk_query_max_x_per_r(self):
        cli_entry("kgtk", "query", "-i", self.file_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "g: (x)-[r]->(y)",
                  "--return", 'r, max(x), r.label, y',
                  "--limit", "5", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')

        self.assertTrue(len(df) == 5)
        ids = list(df['id'].unique())
        self.assertTrue('e11' in ids)
        self.assertTrue('e12' in ids)
        self.assertTrue('e13' in ids)
        self.assertTrue('e14' in ids)
        self.assertTrue('e21' in ids)

    def test_kgtk_query_count(self):
        cli_entry("kgtk", "query", "-i", self.file_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "g: (x)-[r]->(y)",
                  "--where", 'x = "Joe"',
                  "--return", 'count(x) as N', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')

        self.assertTrue(len(df) == 1)
        for i, row in df.iterrows():
            self.assertEqual(row['N'], 3)

    def test_kgtk_query_count_distinct(self):
        cli_entry("kgtk", "query", "-i", self.file_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "g: (x)-[r]->(y)",
                  "--where", 'x = "Joe"',
                  "--return", 'count(distinct x) as N', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 1)
        for i, row in df.iterrows():
            self.assertEqual(row['N'], 1)

    def test_kgtk_query_biggest_salary(self):
        cli_entry("kgtk", "query", "-i", self.works_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "w: (y {salary: s})-[r:works]-(c)",
                  "--return", 'max(cast(s, int)) as `node1;salary`, y, "works" as label, c, r', '--graph-cache',
                  self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 1)
        for i, row in df.iterrows():
            self.assertEqual(row['node1;salary'], 20000)
            self.assertEqual(row['node1'], 'Joe')
            self.assertEqual(row['node2'], 'Kaiser')

    def test_kgtk_query_date_filter(self):
        cli_entry("kgtk", "query", "-i", self.quals_path, "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "(eid)-[q]->(time)", "--where", "time.kgtk_date_year < 2005", '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 4)
        ids = list(df['id'].unique())
        self.assertTrue('m11' in ids)
        self.assertTrue('m12' in ids)
        self.assertTrue('m13' in ids)
        self.assertTrue('m14' in ids)

    def test_kgtk_query_three_graphs(self):
        cli_entry("kgtk", "query", "-i", self.works_path,
                  "-i", self.quals_path,
                  "-i", self.props_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "work: (x)-[r {label: rl}]->(y), qual: (r)-[rp {label: p}]->(time), prop: (p)-[:member]->(:set1)",
                  "--where", 'time.kgtk_date_year <= 2000',
                  "--return", 'r as id, x, rl, y, p as trel, time as time', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 3)
        for i, row in df.iterrows():
            if row['id'] == 'w12':
                self.assertEqual(row['node1'], 'Otto')
                self.assertEqual(row['node2'], 'Kaiser')
                self.assertEqual(row['trel'], 'ends')
                self.assertEqual(row['time'], '^1987-11-08T04:56:34Z/10')

    def test_kgtk_query_property_enumeration_list(self):
        cli_entry("kgtk", "query", "-i", self.works_path,
                  "-i", self.quals_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "work: (x)-[r {label: rl}]->(y), qual: (r)-[rp {label: p}]->(time)",
                  "--where", "p in ['starts', 'ends'] and time.kgtk_date_year <= 2000",
                  "--return", 'r as id, x, rl, y, p as trel, time as time', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 3)
        for i, row in df.iterrows():
            if row['id'] == 'w12':
                self.assertEqual(row['node1'], 'Otto')
                self.assertEqual(row['node2'], 'Kaiser')
                self.assertEqual(row['trel'], 'ends')
                self.assertEqual(row['time'], '^1987-11-08T04:56:34Z/10')

            if row['id'] == 'w11':
                self.assertEqual(row['node1'], 'Hans')
                self.assertEqual(row['node2'], 'ACME')
                self.assertEqual(row['trel'], 'starts')
                self.assertEqual(row['time'], '^1984-12-17T00:03:12Z/11')

    def test_kgtk_query_multi_graph_regex(self):
        cli_entry("kgtk", "query", "-i", self.works_path,
                  "-i", self.quals_path,
                  "-o", f'{self.temp_dir}/out.tsv', "--match",
                  "work: (x)-[r {label: rl}]->(y), qual: (r)-[rp {label: p}]->(time)",
                  "--where", "p =~ 's.*' and time.kgtk_date_year <= 2000",
                  "--return", 'r as id, x, rl, y, p as trel, time as time',
                  "--order-by", 'p desc, time asc', '--graph-cache', self.sqldb)
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 2)
        for i, row in df.iterrows():
            if row['id'] == 'w13':
                self.assertEqual(row['node1'], 'Joe')
                self.assertEqual(row['node2'], 'Kaiser')
                self.assertEqual(row['trel'], 'starts')
                self.assertEqual(row['time'], '^1996-02-23T08:02:56Z/09')

            if row['id'] == 'w11':
                self.assertEqual(row['node1'], 'Hans')
                self.assertEqual(row['node2'], 'ACME')
                self.assertEqual(row['trel'], 'starts')
                self.assertEqual(row['time'], '^1984-12-17T00:03:12Z/11')

    def test_kgtk_query_mod_operator(self):
        cli_entry('kgtk', 'query', '-i', self.file_path,
                  '--graph-cache', self.sqldb,
                  '-o', f'{self.temp_dir}/out.tsv',
                  '--match', '(n1)-[r:name]->(n2)',
                  '--return', 'r, n1, r.label, n2, length(n2) % 3 as rem')
                  
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 5)
        for i, row in df.iterrows():
            if row['id'] == 'e21':
                self.assertEqual(int(row['rem']), 0)
            if row['id'] == 'e22':
                self.assertEqual(int(row['rem']), 0)
            if row['id'] == 'e23':
                self.assertEqual(int(row['rem']), 2)
            if row['id'] == 'e24':
                self.assertEqual(int(row['rem']), 1)
            if row['id'] == 'e25':
                self.assertEqual(int(row['rem']), 0)

    def test_kgtk_query_order_by_alias(self):
        cli_entry('kgtk', 'query', '-i', self.file_path,
                  '--graph-cache', self.sqldb,
                  '-o', f'{self.temp_dir}/out.tsv',
                  '--match', '(n1)-[r:name]->(n2)',
                  '--return', 'r, n1, r.label, n2, length(n2) as `node2;len`',
                  '--order-by', '`node2;len`')
                  
        df = pd.read_csv(f'{self.temp_dir}/out.tsv', sep='\t')
        self.assertTrue(len(df) == 5)
        for i, row in df.iterrows():
            if i == 0:
                self.assertEqual(int(row['node2;len']), 5)
            if i == 1:
                self.assertEqual(int(row['node2;len']), 6)
            if i == 2:
                self.assertEqual(int(row['node2;len']), 7)
            if i == 3:
                self.assertEqual(int(row['node2;len']), 9)
            if i == 4:
                self.assertEqual(int(row['node2;len']), 9)


    ### Testing literal accessors:
    
    def run_literal_access_query(self, query, literals=None, output=None, db=None):
        """Run KGTK 'query' command on literals test data and return the result as a dataframe.
        """
        literals = literals or self.literals_path
        output = output or f'{self.temp_dir}/out.tsv'
        db = db or self.sqldb
        query = query.format(LITERALS=literals, OUTPUT=output, DB=db)
        cli_entry(*shlex.split(query))
        df = pd.read_csv(output, sep='\t')
        return df

    def result_to_dataframe(self, result):
        """Convert one or more 'result' rows into a dataframe.
        """
        if isinstance(result, str):
            result = [result]
        out = StringIO()
        for line in result:
            out.write(line)
            if not line.endswith('\n'):
                out.write('\n')
        df = pd.read_csv(StringIO(out.getvalue()), sep='\t')
        return df

    def assert_literal_access_query_result(self, query, result, rowids=None,
                                           literals=None, output=None, db=None):
        """Assert that the dataframes produced by 'query' and defined by 'result' are the same.
        If 'rowids' is not None, only compare the specified rows.  This currently assumes that
        the rows are in the same order; we could generalize that down the line if necessary.
        """
        qdf = self.run_literal_access_query(query)
        rdf = self.result_to_dataframe(result)
        if rowids is not None:
            if not isinstance(rowids, list):
                rowids = [rowids]
            qdf = qdf.loc[qdf['id'].isin(rowids)]
            rdf = rdf.loc[rdf['id'].isin(rowids)]
        self.assertTrue(qdf.equals(rdf))

    def test_kgtk_query_literal_access_kgtk_string(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:sy1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_string(v) as `node2;is_string`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_string""",
                """esy1\tsy1\tsymbol\tFooBar\t0"""]
        self.assert_literal_access_query_result(query, result)

        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:st1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_string(v) as `node2;is_string`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_string""",
                """est1\tst1\tstring\t"Franz Klammer"\t1"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_stringify(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:sy1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_stringify(v) as `node2;as_string`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;as_string""",
                """esy1\tsy1\tsymbol\tFooBar\t"FooBar\""""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_unstringify(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:st2)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_unstringify(v) as `node2;as_symbol`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;as_symbol""",
                """est2\tst2\tstring\t"KGTK"\tKGTK"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_lqstring(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:st1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring(v) as `node2;is_lqstring`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_lqstring""",
                """est1\tst1\tstring\t"Franz Klammer"\t0"""]
        self.assert_literal_access_query_result(query, result)

        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring(v) as `node2;is_lqstring`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_lqstring""",
                """elq1\tlq1\tlqstring\t'hans'@de\t1"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_lqstring_text(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring_text(v) as `node2;text`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;text""",
                """elq1\tlq1\tlqstring\t'hans'@de\thans"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_lqstring_text_string(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring_text_string(v) as `node2;string`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;string""",
                """elq1\tlq1\tlqstring\t'hans'@de\t"hans\""""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_lqstring_lang(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring_lang(v) as `node2;lang`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;lang""",
                """elq1\tlq1\tlqstring\t'hans'@de\tde"""]
        self.assert_literal_access_query_result(query, result)

        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq2)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring_lang(v) as `node2;lang`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;lang""",
                """elq2\tlq2\tlqstring\t'otto'@de-bav\tde"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_lqstring_suffix(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring_suffix(v) as `node2;suffix`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;suffix""",
                """elq1\tlq1\tlqstring\t'hans'@de"""]
        self.assert_literal_access_query_result(query, result)

        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq2)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring_suffix(v) as `node2;suffix`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;suffix""",
                """elq2\tlq2\tlqstring\t'otto'@de-bav\t-bav"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_lqstring_lang_suffix(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring_lang_suffix(v) as `node2;lang_suffix`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;lang_suffix""",
                """elq1\tlq1\tlqstring\t'hans'@de\tde"""]
        self.assert_literal_access_query_result(query, result)

        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq2)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_lqstring_lang_suffix(v) as `node2;lang_suffix`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;lang_suffix""",
                """elq2\tlq2\tlqstring\t'otto'@de-bav\tde-bav"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:lq1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date(v) as `node2;is_date`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_date""",
                """elq1\tlq1\tlqstring\t'hans'@de\t0"""]
        self.assert_literal_access_query_result(query, result)

        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date(v) as `node2;is_date`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_date""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t1"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_date(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_date(v) as `node2;date`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;date""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t^2020-10-30"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_time(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_time(v) as `node2;time`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;time""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t^02:03:57+10:30"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_and_time(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_and_time(v) as `node2;date_and_time`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;date_and_time""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t^2020-10-30T02:03:57+10:30"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_year(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_year(v) as `node2;year`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;year""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t2020"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_month(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_month(v) as `node2;month`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;month""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t10"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_day(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_day(v) as `node2;day`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;day""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t30"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_hour(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_hour(v) as `node2;hour`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;hour""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t2"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_minutes(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_minutes(v) as `node2;minutes`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;minutes""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t3"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_seconds(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_seconds(v) as `node2;seconds`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;seconds""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t57"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_zone(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_zone(v) as `node2;date_zone`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;date_zone""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t+10:30"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_zone_string(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_zone_string(v) as `node2;zone_string`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;zone_string""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t"+10:30\""""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_date_precision(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:d6)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_date_precision(v) as `node2;precision`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;precision""",
                """ed6\td6\tdate\t^2020-10-30T02:03:57+10:30/9\t9"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_number(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_number(v) as `node2;is_number`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_number""",
                """eq1\tq1\tquantity\t0\t1""",
                """eq2\tq2\tquantity\t0.0\t1""",
                """eq3\tq3\tquantity\t+1234\t1""",
                """eq4\tq4\tquantity\t-12345.1234\t1""",
                """eq5\tq5\tquantity\t4567.12e-10\t1""",
                """eq6\tq6\tquantity\t100m\t0""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t0""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t0"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_quantity(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity(v) as `node2;is_quantity`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_quantity""",
                """eq1\tq1\tquantity\t0\t0""",
                """eq2\tq2\tquantity\t0.0\t0""",
                """eq3\tq3\tquantity\t+1234\t0""",
                """eq4\tq4\tquantity\t-12345.1234\t0""",
                """eq5\tq5\tquantity\t4567.12e-10\t0""",
                """eq6\tq6\tquantity\t100m\t1""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t1""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t1"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_quantity_numeral(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_numeral(v) as `node2;numeral`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;numeral""",
                """eq1\tq1\tquantity\t0\t0""",
                """eq2\tq2\tquantity\t0.0\t0.0""",
                """eq3\tq3\tquantity\t+1234\t+1234""",
                """eq4\tq4\tquantity\t-12345.1234\t-12345.1234""",
                """eq5\tq5\tquantity\t4567.12e-10\t4567.12e-10""",
                """eq6\tq6\tquantity\t100m\t100""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t+1.609344e03""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t1.609344e03"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_quantity_numeral_string(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_numeral_string(v) as `node2;numeral_string`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;numeral_string""",
                """eq1\tq1\tquantity\t0\t"0\"""",
                """eq2\tq2\tquantity\t0.0\t"0.0\"""",
                """eq3\tq3\tquantity\t+1234\t"+1234\"""",
                """eq4\tq4\tquantity\t-12345.1234\t"-12345.1234\"""",
                """eq5\tq5\tquantity\t4567.12e-10\t"4567.12e-10\"""",
                """eq6\tq6\tquantity\t100m\t"100\"""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t"+1.609344e03\"""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t"1.609344e03\""""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_quantity_number(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_number(v) as `node2;number`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;number""",
                """eq1\tq1\tquantity\t0\t0""",
                """eq2\tq2\tquantity\t0.0\t0.0""",
                """eq3\tq3\tquantity\t+1234\t1234""",
                """eq4\tq4\tquantity\t-12345.1234\t-12345.1234""",
                """eq5\tq5\tquantity\t4567.12e-10\t4.56712e-07""",
                """eq6\tq6\tquantity\t100m\t100""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t1609.344""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t1609.344"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_quantity_number_int(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_number_int(v) as `node2;number_int`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;number_int""",
                """eq1\tq1\tquantity\t0\t0""",
                """eq2\tq2\tquantity\t0.0\t0""",
                """eq3\tq3\tquantity\t+1234\t1234""",
                """eq4\tq4\tquantity\t-12345.1234\t-12345""",
                """eq5\tq5\tquantity\t4567.12e-10\t0""",
                """eq6\tq6\tquantity\t100m\t100""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t1609""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t1609"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_quantity_number_float(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_number_float(v) as `node2;number_float`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;number_float""",
                """eq1\tq1\tquantity\t0\t0.0""",
                """eq2\tq2\tquantity\t0.0\t0.0""",
                """eq3\tq3\tquantity\t+1234\t1234.0""",
                """eq4\tq4\tquantity\t-12345.1234\t-12345.1234""",
                """eq5\tq5\tquantity\t4567.12e-10\t4.56712e-07""",
                """eq6\tq6\tquantity\t100m\t100.0""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t1609.344""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t1609.344"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_quantity_si_units(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_si_units(v) as `node2;si_units`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;si_units""",
                """eq1\tq1\tquantity\t0\t""",
                """eq2\tq2\tquantity\t0.0\t""",
                """eq3\tq3\tquantity\t+1234\t""",
                """eq4\tq4\tquantity\t-12345.1234\t""",
                """eq5\tq5\tquantity\t4567.12e-10\t""",
                """eq6\tq6\tquantity\t100m\tm""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\tm""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t"""]
        self.assert_literal_access_query_result(query, result, rowids=['eq5', 'eq6', 'eq7', 'eq8'])

    def test_kgtk_query_literal_access_kgtk_quantity_wd_units(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_wd_units(v) as `node2;wd_units`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;wd_units""",
                """eq1\tq1\tquantity\t0\t""",
                """eq2\tq2\tquantity\t0.0\t""",
                """eq3\tq3\tquantity\t+1234\t""",
                """eq4\tq4\tquantity\t-12345.1234\t""",
                """eq5\tq5\tquantity\t4567.12e-10\t""",
                """eq6\tq6\tquantity\t100m\t""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\tQ11573"""]
        self.assert_literal_access_query_result(query, result, rowids=['eq5', 'eq6', 'eq7', 'eq8'])

    def test_kgtk_query_literal_access_kgtk_quantity_tolerance(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_tolerance(v) as `node2;tolerance`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;tolerance""",
                """eq1\tq1\tquantity\t0\t""",
                """eq2\tq2\tquantity\t0.0\t""",
                """eq3\tq3\tquantity\t+1234\t""",
                """eq4\tq4\tquantity\t-12345.1234\t""",
                """eq5\tq5\tquantity\t4567.12e-10\t""",
                """eq6\tq6\tquantity\t100m\t""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t[-0.1,+0.2]""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t[-0.1,+0.2]"""]
        self.assert_literal_access_query_result(query, result, rowids=['eq5', 'eq6', 'eq7', 'eq8'])

    def test_kgtk_query_literal_access_kgtk_quantity_tolerance_string(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_tolerance_string(v) as `node2;tolerance_string`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;tolerance_string""",
                """eq1\tq1\tquantity\t0\t""",
                """eq2\tq2\tquantity\t0.0\t""",
                """eq3\tq3\tquantity\t+1234\t""",
                """eq4\tq4\tquantity\t-12345.1234\t""",
                """eq5\tq5\tquantity\t4567.12e-10\t""",
                """eq6\tq6\tquantity\t100m\t""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t"[-0.1,+0.2]\"""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t"[-0.1,+0.2]\""""]
        self.assert_literal_access_query_result(query, result, rowids=['eq5', 'eq6', 'eq7', 'eq8'])

    def test_kgtk_query_literal_access_kgtk_quantity_low_tolerance(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_low_tolerance(v) as `node2;low_tolerance`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;low_tolerance""",
                """eq1\tq1\tquantity\t0\t""",
                """eq2\tq2\tquantity\t0.0\t""",
                """eq3\tq3\tquantity\t+1234\t""",
                """eq4\tq4\tquantity\t-12345.1234\t""",
                """eq5\tq5\tquantity\t4567.12e-10\t""",
                """eq6\tq6\tquantity\t100m\t""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t-0.1""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t-0.1"""]
        self.assert_literal_access_query_result(query, result, rowids=['eq5', 'eq6', 'eq7', 'eq8'])

    def test_kgtk_query_literal_access_kgtk_quantity_high_tolerance(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:quantity]->(v)'
                        --return 'r, n1, r.label, v, kgtk_quantity_high_tolerance(v) as `node2;high_tolerance`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;high_tolerance""",
                """eq1\tq1\tquantity\t0\t""",
                """eq2\tq2\tquantity\t0.0\t""",
                """eq3\tq3\tquantity\t+1234\t""",
                """eq4\tq4\tquantity\t-12345.1234\t""",
                """eq5\tq5\tquantity\t4567.12e-10\t""",
                """eq6\tq6\tquantity\t100m\t""",
                """eq7\tq7\tquantity\t+1.609344e03[-0.1,+0.2]m\t0.2""",
                """eq8\tq8\tquantity\t1.609344e03[-0.1,+0.2]Q11573\t0.2"""]
        self.assert_literal_access_query_result(query, result, rowids=['eq5', 'eq6', 'eq7', 'eq8'])

    def test_kgtk_query_literal_access_kgtk_geo_coords(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1:st1)-[r]->(v)'
                        --return 'r, n1, r.label, v, kgtk_geo_coords(v) as `node2;is_geo_coords`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_geo_coords""",
                """est1\tst1\tstring\t"Franz Klammer"\t0"""]
        self.assert_literal_access_query_result(query, result)

        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:geoloc]->(v)'
                        --return 'r, n1, r.label, v, kgtk_geo_coords(v) as `node2;is_geo_coords`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;is_geo_coords""",
                """egl1\tgl1\tgeoloc\t@-42.42/69.123\t1""",
                """egl2\tgl2\tgeoloc\t@19.42/-69.123e-1\t1"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_geo_coords_lat(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:geoloc]->(v)'
                        --return 'r, n1, r.label, v, kgtk_geo_coords_lat(v) as `node2;latitude`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;latitude""",
                """egl1\tgl1\tgeoloc\t@-42.42/69.123\t-42.42""",
                """egl2\tgl2\tgeoloc\t@19.42/-69.123e-1\t19.42"""]
        self.assert_literal_access_query_result(query, result)

    def test_kgtk_query_literal_access_kgtk_geo_coords_long(self):
        query = """kgtk query -i {LITERALS} -o {OUTPUT} --graph-cache {DB}
                        --match  '(n1)-[r:geoloc]->(v)'
                        --return 'r, n1, r.label, v, kgtk_geo_coords_long(v) as `node2;longitude`'
                """
        result=["""id\tnode1\tlabel\tnode2\tnode2;longitude""",
                """egl1\tgl1\tgeoloc\t@-42.42/69.123\t69.123""",
                """egl2\tgl2\tgeoloc\t@19.42/-69.123e-1\t-6.9123"""]
        self.assert_literal_access_query_result(query, result)
