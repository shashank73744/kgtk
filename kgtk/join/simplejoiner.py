"""
Join two KTKG edge files.

Note: This implementation builds im-memory sets of all the node1 values in
each input file.

"""

from argparse import ArgumentParser
import attr
import gzip
from pathlib import Path
from multiprocessing import Queue
import sys
import typing

from kgtk.join.edgewriter import EdgeWriter
from kgtk.join.kgtkreader import KgtkReader
from kgtk.join.kgtkformat import KgtkFormat

@attr.s(slots=True, frozen=True)
class SimpleJoiner(KgtkFormat):
    left_file_path: Path = attr.ib(validator=attr.validators.instance_of(Path))
    right_file_path: Path = attr.ib(validator=attr.validators.instance_of(Path))
    output_path: typing.Optional[Path] = attr.ib(validator=attr.validators.optional(attr.validators.instance_of(Path)))

    # left_join == False and right_join == False: inner join
    # left_join == True and right_join == False: left join
    # left_join == False and right_join == True: right join
    # left_join = True and right_join == True: outer join
    left_join: bool = attr.ib(validator=attr.validators.instance_of(bool), default=False)
    right_join: bool = attr.ib(validator=attr.validators.instance_of(bool), default=False)

    left_join_column_name: typing.Optional[str] = attr.ib(validator=attr.validators.optional(attr.validators.instance_of(str)), default=None)
    right_join_column_name: typing.Optional[str] = attr.ib(validator=attr.validators.optional(attr.validators.instance_of(str)), default=None)

    # Require or fill trailing fields?
    require_all_columns: bool = attr.ib(validator=attr.validators.instance_of(bool), default=True)
    prohibit_extra_columns: bool = attr.ib(validator=attr.validators.instance_of(bool), default=True)
    fill_missing_columns: bool = attr.ib(validator=attr.validators.instance_of(bool), default=False)

    gzip_in_parallel: bool = attr.ib(validator=attr.validators.instance_of(bool), default=False)

    verbose: bool = attr.ib(validator=attr.validators.instance_of(bool), default=False)
    very_verbose: bool = attr.ib(validator=attr.validators.instance_of(bool), default=False)

    def join_column_idx(self, kr: KgtkReader, join_column_name: typing.Optional[str], who: str)->int:
        if join_column_name is not None:
            if join_column_name in kr.column_name_map:
                return kr.column_name_map[join_column_name]
            else:
                # TODO: throw a better exception
                raise ValueError("SimpleJoiner: unknown %s join column %s" % (who, join_column_name))
        else:
            idx: int
            if kr.is_edge_file:
                idx = kr.node1_column_idx
                if idx < 0:
                    # TODO: throw a better exception
                    raise ValueError("SimpleJoiner: unknown node1 column index in KGTK %s edge type." % who)
                return idx
            elif kr.is_node_file:
                idx = kr.id_column_idx
                if idx < 0:
                    # TODO: throw a better exception
                    raise ValueError("SimpleJoiner: unknown node1 column index in KGTK %s node type." % who)
                return idx
            else:
                # TODO: throw a better exception
                raise ValueError("SimpleJoiner: unknown %s KGTK file type." % who)

    def join_column_set(self, kr: KgtkReader, join_column_idx: int)->typing.Set[str]:
        result: typing.Set[str] = set()
        for line in kr:
            result.add(line[join_column_idx])
        return result
        
    def extract_join_values(self, file_path: Path, join_column_name: typing.Optional[str], who: str)->typing.Set[str]:
        kr: KgtkReader = KgtkReader.open(file_path,
                                         require_all_columns=self.require_all_columns,
                                         prohibit_extra_columns=self.prohibit_extra_columns,
                                         fill_missing_columns=self.fill_missing_columns,
                                         gzip_in_parallel=self.gzip_in_parallel,
                                         verbose=self.verbose,
                                         very_verbose=self.very_verbose)
        
        return self.join_column_set(kr, self.join_column_idx(kr, join_column_name, who)) # closes er file
        

    def join_column_values(self)->typing.Set[str]:
        """
        Read the input edge files the first time, building the sets of left and right join values.
        """
        left_join_values: typing.Set[str] = self.extract_join_values(self.left_file_path, self.left_join_column_name, "left")
        right_join_values: typing.Set[str] = self.extract_join_values(self.right_file_path, self.right_join_column_name, "right")

        joined_column_values: typing.Set[str]
        if self.left_join and self.right_join:
            # TODO: This joins everything! We can shortut computing these sets.
            joined_column_values = left_join_values.union(right_join_values)
        elif self.left_join and not self.right_join:
            joined_column_values = left_join_values.copy()
        elif self.right_join and not self.left_join:
            joined_column_values = right_join_values.copy()
        else:
            joined_column_values = left_join_values.intersection(right_join_values)
        return joined_column_values
    
    def process(self):
        joined_column_values: typing.Set[str] = self.join_column_values()

        # Open the input files for the second time. This won't work with stdin.
        left_kr: KgtkReader =  KgtkReader.open(self.left_file_path,
                                               require_all_columns=self.require_all_columns,
                                               prohibit_extra_columns=self.prohibit_extra_columns,
                                               fill_missing_columns=self.fill_missing_columns)
        right_kr: EdgeReader = KgtkReader.open(self.right_file_path,
                                               require_all_columns=self.require_all_columns,
                                               prohibit_extra_columns=self.prohibit_extra_columns,
                                               fill_missing_columns=self.fill_missing_columns)
        joined_column_names: typing.list[str] = left_kr.merge_columns(right_kr.additional_column_names())
        
        ew: EdgeWriter = EdgeWriter.open(joined_column_names,
                                         self.output_path,
                                         require_all_columns=False,
                                         prohibit_extra_columns=True,
                                         fill_missing_columns=True,
                                         gzip_in_parallel=self.gzip_in_parallel,
                                         verbose=self.verbose,
                                         very_verbose=self.very_verbose)

        line: typing.list[str]
        left_node1_idx: int = self.join_column_idx(left_kr, self.left_join_column_name, who="left")
        for line in left_kr:
            node1_value: str = line[left_node1_idx]
            if node1_value in joined_column_values:
                ew.write(line)

        right_shuffle_list: typing.List[int] = ew.build_shuffle_list(right_kr.column_names)
        right_node1_idx: int = self.join_column_idx(right_kr, self.right_join_column_name, who="right")
        for line in right_kr:
            node1_value: str = line[right_node1_idx]
            if node1_value in joined_column_values:
                ew.write(line, shuffle_list=right_shuffle_list)
            
        ew.close()
        
def main():
    """
    Test the KGTK file joiner.
    """
    parser = ArgumentParser()
    parser.add_argument(dest="left_file_path", help="The KGTK file to read", type=Path)
    parser.add_argument(dest="right_file_path", help="The KGTK file to read", type=Path)
    parser.add_argument("-o", "--output-file", dest="output_file_path", help="The KGTK file to read", type=Path, default=None)
    parser.add_argument(      "--gzip-in-parallel", dest="gzip_in_parallel", help="Execute gzip in parallel.", action='store_true')
    parser.add_argument(      "--left-join", dest="left_join", help="Perform a left outer join.", action='store_true')
    parser.add_argument(      "--left-join-column-name", dest="left_join_column_name", help="The name of the left join column.")
    parser.add_argument(      "--right-join", dest="right_join", help="Perform a right outer join.", action='store_true')
    parser.add_argument(      "--right-join-column-name", dest="right_join_column_name", help="The name of the right join column.")
    parser.add_argument("-v", "--verbose", dest="verbose", help="Print additional progress messages.", action='store_true')
    parser.add_argument(      "--very-verbose", dest="very_verbose", help="Print additional progress messages.", action='store_true')
    args = parser.parse_args()

    ej: SimpleJoiner = SimpleJoiner(left_file_path=args.left_file_path,
                                    right_file_path=args.right_file_path,
                                    output_path=args.output_file_path,
                                    left_join=args.left_join,
                                    right_join=args.right_join,
                                    left_join_column_name=args.left_join_column_name,
                                    right_join_column_name=args.right_join_column_name,
                                    gzip_in_parallel=args.gzip_in_parallel,
                                    verbose=args.verbose,
                                    very_verbose=args.very_verbose)

    ej.process()

if __name__ == "__main__":
    main()
