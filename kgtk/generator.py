import re
import json
import gzip
import rfc3986
from etk.etk import ETK
from etk.etk_module import ETKModule
from etk.wikidata.statement import Rank
from etk.knowledge_graph import KGSchema
from etk.wikidata import wiki_namespaces
from kgtk.exceptions import KGTKException
from etk.wikidata.entity import WDItem, WDProperty

from etk.wikidata.value import (
    Precision,
    Item,
    StringValue,
    TimeValue,
    QuantityValue,
    MonolingualText,
    GlobeCoordinate,
    ExternalIdentifier,
    URLValue
)
from etk.knowledge_graph.node import LiteralType
import warnings

BAD_CHARS = [":", "&", ",", " ",
             "(", ")", "\'", '\"', "/", "\\", "[", "]", ";", "|"]


class Generator:
    def __init__(self, **kwargs):
        label_set = kwargs.pop("label_set")
        description_set = kwargs.pop("description_set")
        alias_set = kwargs.pop("alias_set")
        n = int(kwargs.pop("n"))
        warning = kwargs.pop("warning")
        log_path = kwargs.pop("log_path")
        self.prop_file = kwargs.pop("prop_file")
        self.read_num_of_lines = 0
        # set sets
        self.set_sets(label_set, description_set, alias_set)
        # column name order_map
        self.order_map = {}
        self.n = n
        self.yyyy_mm_dd_pattern = re.compile(
            r"[12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
        self.yyyy_pattern = re.compile(r"[12]\d{3}")
        self.quantity_pattern = re.compile(
            r"([\+|\-]?[0-9]+\.?[0-9]*[e|E]?[\-]?[0-9]*)(?:\[([\+|\-]?[0-9]+\.?[0-9]*),([\+|\-]?[0-9]+\.?[0-9]*)\])?([U|Q](?:.*))?")
        self.warning = warning
        if self.warning:
            self.warn_log = open(log_path, "w")
        self.to_append_statement_id = None
        self.corrupted_statement_id = None
        self.to_append_statement = None  # for Json generator
        self.wiki_import_prop_types = set(["wikipedia_sitelink", "language"])

    def serialize(self):
        raise NotImplemented

    def finalize(self):
        if self.warning:
            self.warn_log.close()
        self.serialize()

    def set_sets(self, label_set: str, description_set: str, alias_set: str):
        self.label_set, self.alias_set, self.description_set = set(label_set.split(",")), set(
            alias_set.split(",")), set(description_set.split(","))

    def initialize_order_map(self, edge: str):
        edge_list = edge.strip("\r\n").split("\t")
        node1_index = edge_list.index("node1")
        node2_index = edge_list.index("node2")
        prop_index = edge_list.index("label")
        id_index = edge_list.index("id")
        if not all([node1_index > -1, node2_index > -1, prop_index > -1, id_index > -1]):
            raise KGTKException(
                "Header of kgtk file misses at least one of required column names: (node1, node2, property and id)")
        else:
            self.order_map["node1"] = node1_index
            self.order_map["node2"] = node2_index
            self.order_map["label"] = prop_index
            self.order_map["id"] = id_index
            if hasattr(self, 'has_rank') and self.has_rank == True:
                rank_index = edge_list.index("rank")
                self.order_map["rank"] = rank_index

    def parse_edges(self, edge: str):
        # use the order_map to map the node
        edge_list = edge.strip("\r\n").split("\t")
        try:
            node1 = edge_list[self.order_map["node1"]].strip()
            node2 = edge_list[self.order_map["node2"]].strip()
            prop = edge_list[self.order_map["label"]].strip()
            e_id = edge_list[self.order_map["id"]].strip()
        except:
            print(edge_list)
        return node1, node2, prop, e_id

    @staticmethod
    def process_text_string(string: str) -> [str, str]:
        ''' 
        Language detection is removed from triple generation. The user is responsible for detect the language
        '''
        if len(string) == 0:
            return ["", "en"]
        if "@" in string:
            res = string.split("@")
            text_string = "@".join(res[:-1]).replace('"', "").replace("'", "")
            lang = res[-1].replace('"', '').replace("'", "")
        else:
            text_string = string.replace('"', "").replace("'", "")
            lang = "en"
        return [text_string, lang]

    @staticmethod
    def is_invalid_decimal_string(num_string) -> bool:
        '''
        if a decimal string too small, return True TODO
        '''
        if num_string == None:
            return False
        else:
            if abs(float(num_string)) < 0.0001 and float(num_string) != 0:
                return True
            return False

    @staticmethod
    def is_valid_uri_with_scheme_and_host(uri: str) -> bool:
        '''
        https://github.com/python-hyper/rfc3986/issues/30#issuecomment-461661883
        '''
        try:
            uri = rfc3986.URIReference.from_string(uri)
            rfc3986.validators.Validator().require_presence_of(
                "scheme", "host").check_validity_of("scheme", "host").validate(uri)
            return True
        except:
            return False

    @staticmethod
    def clean_number_string(num: str) -> str:
        from numpy import format_float_positional
        if num == None:
            return None
        else:
            return format_float_positional(float(num), trim="-")

    @staticmethod
    def replace_illegal_string(s: str) -> str:
        '''
        this function serves as the last gate of keeping illegal characters outside of entity creation.
        '''
        for char in BAD_CHARS:
            s = s.replace(char, "_")
        return s


class TripleGenerator(Generator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        prop_declaration = kwargs.pop("prop_declaration")
        dest_fp = kwargs.pop("dest_fp")
        truthy = kwargs.pop("truthy")
        use_id = kwargs.pop("use_id")
        prefix_path = kwargs.pop("prefix_path")
        self.datatype_mapping = {
            # nomenclature from https://w.wiki/Tfn
            "item": Item,
            "WikibaseItem": Item,
            "wikibase-item": Item,

            "time": TimeValue,
            "Time": TimeValue,

            "globe-coordinate": GlobeCoordinate,
            "GlobeCoordinate": GlobeCoordinate,

            "quantity": QuantityValue,
            "Quantity": QuantityValue,

            "monolingualtext": MonolingualText,
            "Monolingualtext": MonolingualText,

            "string": StringValue,
            "String": StringValue,

            "external-identifier": ExternalIdentifier,
            "ExternalId": ExternalIdentifier,
            "external-id": ExternalIdentifier,

            "url": StringValue,  # TODO bug potentially in rdflib
            "Url": StringValue,

            "property": WDProperty,
            "WikibaseProperty": WDProperty,
            "wikibase-property": WDProperty
        }
        self.set_prefix(prefix_path)
        self.prop_declaration = prop_declaration
        self.set_properties(self.prop_file)
        self.fp = dest_fp
        self.truthy = truthy
        self.reset_etk_doc()
        self.serialize_prefix()
        self.use_id = use_id

    def set_prefix(self, prefix_path: str):
        self.prefix_dict = {}
        if prefix_path != "NONE":
            with open(prefix_path, "r") as fp:
                for line_num, edge in enumerate(fp):
                    edge_list = edge.strip("\r\n").split("\t")
                    if line_num == 0:
                        node1_index, node2_index = edge_list.index("node1"), edge_list.index("node2")
                    else:
                        prefix, expand = edge_list[node1_index], edge_list[node2_index]
                        self.prefix_dict[prefix] = expand

    def read_prop_declaration(self, line_number: int, edge: str):
        node1, node2, prop, e_id = self.parse_edges(edge)
        if prop == "data_type":
            self.prop_types[node1] = self.datatype_mapping[node2.strip()]
        return

    def set_properties(self, prop_file: str):
        self.prop_types = dict()
        if prop_file == "NONE":
            return

        if prop_file.endswith(".gz"):
            fp = gzip.open(prop_file, 'rt')
        else:
            fp = open(prop_file, "r")

        node1_idx = -1
        node2_idx = -1

        for line in fp:
            vals = line.split('\t')
            vals = [v.strip() for v in vals]
            if 'node1' in vals and 'node2' in vals:
                node1_idx = vals.index('node1')
                node2_idx = vals.index('node2')

            else:
                node1 = vals[node1_idx]
                node2 = vals[node2_idx]
                try:
                    self.prop_types[node1] = self.datatype_mapping[node2.strip()]
                except:
                    self.prop_types[node1] = StringValue
                    self.warn_log.write(
                        "DataType {} of node {} is not supported.\n".format(
                            node2, node1
                        )
                    )

    def _node_2_entity(self, node: str):
        '''
        A node can be Qxxx or Pxxx, return the proper entity.
        '''
        if node in self.prop_types:
            entity = WDProperty(node, self.prop_types[node])
        else:
            entity = WDItem(TripleGenerator.replace_illegal_string(node))
        return entity

    def reset_etk_doc(self, doc_id: str = "http://isi.edu/default-ns/projects"):
        """
        reset the doc object and return it. Called at initialization and after outputting triples.
        """
        kg_schema = KGSchema()
        kg_schema.add_schema("@prefix : <http://isi.edu/> .", "ttl")
        self.etk = ETK(kg_schema=kg_schema, modules=ETKModule)
        self.doc = self.etk.create_document({}, doc_id=doc_id)
        for k, v in wiki_namespaces.items():
            if k in self.prefix_dict:
                self.doc.kg.bind(k, self.prefix_dict[k])
            else:
                self.doc.kg.bind(k, v)

    def serialize(self):
        """
        Seriealize the triples. Used a hack to avoid serializing the prefix again.
        """
        docs = self.etk.process_ems(self.doc)
        self.fp.write("\n\n".join(
            docs[0].kg.serialize("ttl").split("\n\n")[1:]))
        self.fp.flush()
        self.reset()

    def serialize_prefix(self):
        """
        This function should be called only once after the doc object is initialized.
        In order to serialize the prefix at the very begining it has to be printed per the change of rdflib 4.2.2->5.0.0
        Relevent issue: https://github.com/RDFLib/rdflib/issues/965
        """
        for k, v in wiki_namespaces.items():
            if k in self.prefix_dict:
                line = "@prefix " + k + ": <" + self.prefix_dict[k] + "> .\n"
            else:
                line = "@prefix " + k + ": <" + v + "> .\n"
            self.fp.write(line)
        self.fp.write("\n")
        self.fp.flush()
        self.reset()

    def reset(self):
        self.to_append_statement_id = None
        self.to_append_statement = None
        self.read_num_of_lines = 0
        self.reset_etk_doc()

    def generate_label_triple(self, node1: str, node2: str) -> bool:
        entity = self._node_2_entity(node1)
        text_string, lang = TripleGenerator.process_text_string(node2)
        entity.add_label(text_string, lang=lang)
        self.doc.kg.add_subject(entity)
        return True

    def generate_description_triple(self, node1: str, node2: str) -> bool:
        entity = self._node_2_entity(node1)
        text_string, lang = TripleGenerator.process_text_string(node2)
        entity.add_description(text_string, lang=lang)
        self.doc.kg.add_subject(entity)
        return True

    def generate_alias_triple(self, node1: str, node2: str) -> bool:
        entity = self._node_2_entity(node1)
        text_string, lang = TripleGenerator.process_text_string(node2)
        entity.add_alias(text_string, lang=lang)
        self.doc.kg.add_subject(entity)
        return True

    def generate_prop_declaration_triple(self, node1: str, node2: str) -> bool:
        # update the known prop_types
        if node1 in self.prop_types:
            if not self.prop_declaration:
                raise KGTKException("Duplicated property definition of {} found!".format(node1))
        else:
            self.prop_types[node1] = node2

        prop = WDProperty(node1, self.datatype_mapping[node2])
        self.doc.kg.add_subject(prop)
        return True

    def generate_normal_triple(
            self, node1: str, property: str, node2: str, is_qualifier_edge: bool, e_id: str, line_number: int) -> bool:
        if self.use_id:
            e_id = TripleGenerator.replace_illegal_string(e_id)
        entity = self._node_2_entity(node1)
        edge_type = self.prop_types[property]
        if edge_type == Item:
            object = WDItem(TripleGenerator.replace_illegal_string(node2))
        elif edge_type == WDProperty:
            object = WDProperty(TripleGenerator.replace_illegal_string(node2), self.prop_types[node2])

        elif edge_type == TimeValue:
            if self.yyyy_mm_dd_pattern.match(node2):
                try:
                    dateTimeString = node2
                    object = TimeValue(
                        value=dateTimeString,  # TODO
                        calendar=Item("Q1985727"),
                        precision=Precision.year,
                        time_zone=0,
                    )
                except:
                    return False
            elif self.yyyy_pattern.match(node2):
                try:
                    dateTimeString = node2 + "-01-01"
                    object = TimeValue(
                        value=dateTimeString,  # TODO
                        calendar=Item("Q1985727"),
                        precision=Precision.year,
                        time_zone=0,
                    )
                except:
                    return False
            else:
                try:
                    # TODO, in future, the two cases above will be dropped in principle to comply with the iso format
                    # now it is iso format
                    assert (node2[0] == "^")
                    node2 = node2[1:]  # remove ^
                    if node2.startswith("+"):
                        node2 = node2[1:]
                    dateTimeString, precision = node2.split("/")
                    dateTimeString = dateTimeString[:-1]  # remove Z
                    object = TimeValue(
                        value=dateTimeString,
                        calendar=Item("Q1985727"),
                        precision=precision,
                        time_zone=0,
                    )
                except:
                    return False

        elif edge_type == GlobeCoordinate:
            latitude, longitude = node2[1:].split("/")
            latitude = float(latitude)
            longitude = float(longitude)
            object = GlobeCoordinate(
                latitude, longitude, 0.0001, globe=Item("Q2"))  # earth

        elif edge_type == QuantityValue:
            # +70[+60,+80]Q743895
            try:
                res = self.quantity_pattern.match(node2)
                if self.warning and res == None:
                    warnings.warn("Node2 [{}] at line [{}] is not a legal quantity. Skipping it.\n".format(
                        node2, line_number))

                    return False
                res = res.groups()

            except:
                raise KGTKException(
                    "Node2 [{}] at line [{}] is not a legal quantity.\n".format(
                        node2, line_number)
                )

            amount, lower_bound, upper_bound, unit = res

            amount = TripleGenerator.clean_number_string(amount)
            num_type = self.xsd_number_type(amount)

            lower_bound = TripleGenerator.clean_number_string(lower_bound)
            upper_bound = TripleGenerator.clean_number_string(upper_bound)
            if unit != None:
                if upper_bound != None and lower_bound != None:
                    object = QuantityValue(amount, unit=Item(
                        unit), upper_bound=upper_bound, lower_bound=lower_bound, type=num_type)
                else:
                    object = QuantityValue(amount, unit=Item(unit), type=num_type)
            else:
                if upper_bound != None and lower_bound != None:
                    object = QuantityValue(
                        amount, upper_bound=upper_bound, lower_bound=lower_bound, type=num_type)
                else:
                    object = QuantityValue(amount, type=num_type)

        elif edge_type == MonolingualText:
            text_string, lang = TripleGenerator.process_text_string(node2)
            object = MonolingualText(text_string, lang)
        elif edge_type == ExternalIdentifier:
            object = ExternalIdentifier(node2)
        elif edge_type == URLValue:
            if TripleGenerator.is_valid_uri_with_scheme_and_host(node2):
                object = URLValue(node2)
            else:
                return False
        else:
            # treat everything else as stringValue
            object = StringValue(node2)

        if type(object) == WDItem or type(object) == WDProperty:
            self.doc.kg.add_subject(object)

        if is_qualifier_edge:
            # edge: e8 p9 ^2013-01-01T00:00:00Z/11
            # create qualifier edge on previous STATEMENT and return the updated STATEMENT
            self.to_append_statement.add_qualifier(property, object)
            self.doc.kg.add_subject(self.to_append_statement)
        else:
            # edge: q1 p8 q2 e8
            # create brand new property edge and replace STATEMENT
            if self.truthy:
                self.to_append_statement = entity.add_truthy_statement(
                    property, object, statement_id=e_id) if self.use_id else entity.add_truthy_statement(property,
                                                                                                         object)
            else:
                self.to_append_statement = entity.add_statement(
                    property, object, statement_id=e_id) if self.use_id else entity.add_statement(property, object)
            self.doc.kg.add_subject(entity)
        return True

    def entry_point(self, line_number: int, edge: str):
        # print(line_number,edge)
        """
        generates a list of two, the first element is the determination of the edge type using corresponding edge type
        the second element is a bool indicating whether this is a valid property edge or qualifier edge.
        Call corresponding downstream functions
        """
        if line_number == 1:
            # initialize the order_map
            self.initialize_order_map(edge)
            return

        # use the order_map to map the node
        node1, node2, prop, e_id = self.parse_edges(edge)
        if line_number == 2:
            # by default a statement edge
            is_qualifier_edge = False
        else:
            if node1 != self.to_append_statement_id and node1 != self.corrupted_statement_id:
                is_qualifier_edge = False
                # also a new statement edge
                if self.read_num_of_lines >= self.n:
                    self.serialize()
            else:
                # qualifier edge or property declaration edge
                is_qualifier_edge = True
                if node1 == self.corrupted_statement_id:
                    self.warn_log.write(
                        "QUALIFIER edge at line [{}] associated of corrupted statement edge of id [{}] dropped.\n".format(
                            line_number, self.corrupted_statement_id
                        )
                    )
                    return
        if prop in self.label_set:
            success = self.generate_label_triple(node1, node2)
        elif prop in self.description_set:
            success = self.generate_description_triple(node1, node2)
        elif prop in self.alias_set:
            success = self.generate_alias_triple(node1, node2)
        elif prop == "data_type" or prop == 'datatype':
            # special edge of prop declaration
            success = self.generate_prop_declaration_triple(
                node1, node2)
        else:
            if prop in self.prop_types:
                success = self.generate_normal_triple(
                    node1, prop, node2, is_qualifier_edge, e_id, line_number)
            else:
                raise KGTKException(
                    "property [{}]'s type is unknown at line [{}].\n".format(
                        prop, line_number)
                )
        if (not success) and self.warning:
            if not is_qualifier_edge:
                self.warn_log.write(
                    "CORRUPTED_STATEMENT edge at line: [{}] with edge id [{}].\n".format(
                        line_number, e_id))
                self.corrupted_statement_id = e_id
            else:
                self.warn_log.write(
                    "CORRUPTED_QUALIFIER edge at line: [{}] with edge id [{}].\n".format(
                        line_number, e_id))

        else:
            self.read_num_of_lines += 1
            if not is_qualifier_edge:
                self.to_append_statement_id = e_id

    @staticmethod
    def xsd_number_type(num):
        if isinstance(num, float) and 'e' in str(num).lower():
            return LiteralType.double
        return LiteralType.decimal


class JsonGenerator(Generator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prop_declaration = kwargs.pop("prop_declaration")
        self.output_prefix = kwargs.pop("output_prefix")
        self.has_rank = kwargs.pop("has_rank")
        self.file_num = 0
        # this data_type mapping is to comply with the SQID UI parsing requirements
        self.datatype_mapping = {
            "item": "wikibase-item",
            "WikibaseItem": "wikibase-item",
            "wikibase-item": "wikibase-item",

            "property": "wikibase-item",
            "WikibaseProperty": "wikibase-item",
            "wikibase-property": "wikibase-item",

            "time": "time",
            "Time": "time",

            "globe-coordinate": "globe-coordinate",
            "GlobeCoordinate": "globe-coordinate",

            "quantity": "quantity",
            "Quantity": "quantity",

            "monolingualtext": "monolingualtext",
            "Monolingualtext": "monolingualtext",

            "string": "string",
            "String": "string",

            "external-identifier": "external-id",
            "ExternalId": "external-id",
            "external-id": "external-id",

            "url": "url",
            "Url": "url"
        }
        self.set_properties(self.prop_file)
        self.set_json_dict()
        self.previous_qnode = None

    def entry_point(self, line_number, edge):
        self.read_num_of_lines += 1
        if line_number == 1:
            self.initialize_order_map(edge)
            return
        edge_list = edge.strip("\r\n").split("\t")
        node1 = edge_list[self.order_map["node1"]].strip()
        node2 = edge_list[self.order_map["node2"]].strip()
        prop = edge_list[self.order_map["label"]].strip()
        e_id = edge_list[self.order_map["id"]].strip()
        if self.has_rank:
            rank = edge_list[self.order_map["rank"]].strip()
        else:
            rank = "normal"  # TODO default rank

        # property declaration
        if prop == "data_type":
            if self.prop_declaration:
                self.prop_types[node1] = self.datatype_mapping[node2.strip()]
                return
            else:
                if self.warning:
                    self.warn_log.write(
                        "CORRUPTED_STATEMENT property declaration edge at line: [{}] with edge id [{}].\n".format(
                            line_number, e_id))

        # add qualifier logic
        if line_number == 2:
            self.previous_qnode = node1
            is_qualifier_edge = False
        else:
            if node1 != self.to_append_statement_id and node1 != self.corrupted_statement_id:
                is_qualifier_edge = False
                # partial serialization
                if self.read_num_of_lines >= self.n:
                    if self.previous_qnode != node1:
                        self.serialize()
                    # update previous qnode to avoid breaking continuous same-qnode statements into two jsonl files
                self.previous_qnode = node1
            else:
                is_qualifier_edge = True
                if node1 == self.corrupted_statement_id:
                    if self.warning:
                        self.warn_log.write(
                            "QUALIFIER edge at line [{}] associated with corrupted statement edge of id [{}] dropped.\n".format(
                                line_number, self.corrupted_statement_id)
                        )

        # update info_json_dict
        if not is_qualifier_edge:
            if node1 in self.prop_types:
                success = self.update_misc_json_dict_info(node1, line_number, self.prop_types[node1])
            else:
                success = self.update_misc_json_dict_info(node1, line_number, None)
            assert (success)

        if prop in self.prop_types:
            success = self.update_misc_json_dict_info(prop, line_number, self.prop_types[prop])
            assert (success)
            if self.prop_types[prop] == "wikibase-item":
                success = self.update_misc_json_dict_info(node2, line_number, None)
                assert (success)

        # update label_json_dict
        if prop in self.label_set:
            success = self.update_misc_json_dict(node1, prop, node2, line_number, rank, "label")
            assert (success)
            return

        # update alias and descriptions
        if prop in self.description_set:
            success = self.update_misc_json_dict(node1, prop, node2, line_number, rank, "description")
            assert (success)
            return

        if prop in self.alias_set:
            success = self.update_misc_json_dict(node1, prop, node2, line_number, rank, "alias")
            assert (success)
            return

            # normal update for claims & qualifiers
        if is_qualifier_edge:
            success = self.update_misc_json_dict(node1, prop, node2, line_number, rank, "qualifier")
        else:
            success = self.update_misc_json_dict(node1, prop, node2, line_number, rank, "statement")

        if (not success) and self.warning:
            if not is_qualifier_edge:
                self.warn_log.write(
                    "CORRUPTED_STATEMENT edge at line: [{}] with edge id [{}].\n".format(
                        line_number, e_id))
                self.corrupted_statement_id = e_id
            else:
                self.warn_log.write(
                    "CORRUPTED_QUALIFIER edge at line: [{}] with edge id [{}].\n".format(
                        line_number, e_id))
        else:
            # success
            if not is_qualifier_edge:
                self.to_append_statement_id = e_id
                self.to_append_statement = [node1, prop]  # path in dictionary for adding future qualifiers

    def init_entity_in_json(self, node: str):
        self.misc_json_dict[node] = {}
        self.misc_json_dict[node]["labels"] = {}
        self.misc_json_dict[node]["descriptions"] = {}
        self.misc_json_dict[node]["aliases"] = {}
        self.misc_json_dict[node]["claims"] = {}
        self.misc_json_dict[node]["sitelinks"] = {}
        if node not in self.prop_types:
            label_type = "item"
        else:
            label_type = "property"
            label_datatype = self.prop_types[node]
            self.misc_json_dict[node]["datatype"] = label_datatype
        self.misc_json_dict[node]["type"] = label_type
        self.misc_json_dict[node]["id"] = node

    def update_misc_json_dict_info(self, node: str, line_number: int, data_type=None):
        if node not in self.misc_json_dict:
            self.init_entity_in_json(node)

        if node.startswith("Q"):
            self.misc_json_dict[node].update(
                {
                    "pageid": -1,
                    "ns": -1,
                    "title": node,
                    "lastrevid": "2000-01-01T00:00:00Z",
                    "type": "item",
                    "id": node}
            )
        elif node.startswith("P"):
            self.misc_json_dict[node].update(
                {
                    "pageid": -1,
                    "ns": -1,
                    "title": "Property:" + node,
                    "lastrevid": "2000-01-01T00:00:00Z",
                    "type": "property",
                    "datatype": data_type,
                    "id": node}
            )
        else:
            if self.warning:
                self.warn_log.write(
                    "node [{}] at line [{}] is neither an entity nor a property.\n".format(node, line_number))
        return True

    def update_misc_json_dict(self, node1: str, prop: str, node2: str, line_number: int, rank: str, field: str):
        if node1 not in self.misc_json_dict and field != "qualifier":
            self.init_entity_in_json(node1)

        if field == "label":
            label_text, lang = JsonGenerator.process_text_string(node2)
            temp_des_dict = {lang: {"languange": lang, "value": label_text}}
            self.misc_json_dict[node1]["labels"].update(temp_des_dict)
            return True

        if field == "description":
            description_text, lang = JsonGenerator.process_text_string(node2)
            temp_des_dict = {lang: {"languange": lang, "value": description_text}}
            self.misc_json_dict[node1]["descriptions"].update(temp_des_dict)
            return True

        if field == "alias":
            alias_text, lang = JsonGenerator.process_text_string(node2)
            temp_alias_dict = {lang: {"languange": lang, "value": alias_text}}
            if lang in self.misc_json_dict[node1]["aliases"]:
                self.misc_json_dict[node1]["aliases"][lang].append(temp_alias_dict)
            else:
                self.misc_json_dict[node1]["aliases"][lang] = [temp_alias_dict]
            return True

        if field == "statement":
            is_qualifier_edge = False
        elif field == "qualifier":
            is_qualifier_edge = True

        if prop not in self.prop_types:
            if prop in self.wiki_import_prop_types:
                if self.warning:
                    self.warn_log.write(
                        "Property {} created by wikidata json dump at line {} is skipped.\n".format(prop, line_number))
                return True
            else:
                raise KGTKException("property {} at line {} is not defined.".format(prop, line_number))

        if not is_qualifier_edge:
            if prop not in self.misc_json_dict[node1]["claims"]:
                self.misc_json_dict[node1]["claims"][prop] = []
        try:
            if self.prop_types[prop] == "wikibase-item":
                object = self.update_misc_json_dict_item(node1, prop, node2, rank, is_qualifier_edge)
            elif self.prop_types[prop] == "time":
                # print("matched date format yyyy-mm-dd",node1,prop,node2,is_qualifier_edge)
                object = self.update_misc_json_dict_time(node1, prop, node2, rank, is_qualifier_edge)
            elif self.prop_types[prop] == "globe-coordinate":
                object = self.update_misc_json_dict_coordinate(node1, prop, node2, rank, is_qualifier_edge)
            elif self.prop_types[prop] == "quantity":
                object = self.update_misc_json_dict_quantity(node1, prop, node2, rank, is_qualifier_edge)
            elif self.prop_types[prop] == "monolingualtext":
                object = self.update_misc_json_dict_monolingualtext(node1, prop, node2, rank, is_qualifier_edge)
            elif self.prop_types[prop] == "string":
                object = self.update_misc_json_dict_string(node1, prop, node2, rank, is_qualifier_edge)
            elif self.prop_types[prop] == "external-id":
                object = self.update_misc_json_dict_external_id(node1, prop, node2, rank, is_qualifier_edge)
            elif self.prop_types[prop] == "url":
                object = self.update_misc_json_dict_url(node1, prop, node2, rank, is_qualifier_edge)
            else:
                raise KGTKException(
                    "property tyepe {} of property {} at line {} is not defined.".format(self.prop_types[prop], prop,
                                                                                         line_number))

            if not object:
                if self.warning:
                    self.warn_log.write("edge creation error at line [{}].\n".format(line_number))
                return False

            # process object
            if is_qualifier_edge:
                # update qualifier edge
                if prop in self.misc_json_dict[self.to_append_statement[0]]["claims"][self.to_append_statement[1]][-1][
                    "qualifiers"]:
                    self.misc_json_dict[self.to_append_statement[0]]["claims"][self.to_append_statement[1]][-1][
                        "qualifiers"][prop].append(object)
                else:
                    self.misc_json_dict[self.to_append_statement[0]]["claims"][self.to_append_statement[1]][-1][
                        "qualifiers"][prop] = [object]
                if prop not in (
                        self.misc_json_dict[self.to_append_statement[0]]["claims"][self.to_append_statement[1]][-1][
                            "qualifiers-order"]):
                    self.misc_json_dict[self.to_append_statement[0]]["claims"][self.to_append_statement[1]][-1][
                        "qualifiers-order"].append(prop)
            else:
                self.misc_json_dict[node1]["claims"][prop].append(object)
            return True

        except:
            raise KGTKException("illegal edge at line {}.".format(line_number))

    def update_misc_json_dict_item(self, node1: str, prop: str, node2: str, rank: str, is_qualifier_edge: bool):
        if not is_qualifier_edge:
            temp_item_dict = {
                "mainsnak": {
                    "snaktype": "value",
                    "property": prop,
                    "hash": "",
                    "datavalue": {
                        "value": {
                            "entity-type": "item",
                            "numeric-id": 0,
                            "id": node2
                        },
                        "type": "wikibase-entityid"
                    },
                    "datatype": "wikibase-item"
                },
                "type": "statement",
                "id": node1 + prop + node2,
                "rank": rank,  # TODO
                "references": [],
                "qualifiers": {},
                "qualifiers-order": []
            }
        else:
            temp_item_dict = {
                "snaktype": "value",
                "property": prop,
                "hash": "",
                "datavalue": {
                    "value": {
                        "entity-type": "item",
                        "numeric-id": 0,
                        "id": node2
                    },
                    "type": "wikibase-entityid"
                },
                "datatype": "wikibase-item"
            }
        return temp_item_dict

    def update_misc_json_dict_time(self, node1: str, prop: str, node2: str, rank: str, is_qualifier_edge: bool):
        if self.yyyy_mm_dd_pattern.match(node2):
            time_string = node2 + "-00-00T00:00:00Z"
            precision = 11
        elif self.yyyy_pattern.match(node2):
            time_string = node2 + "-01-01T00:00:00Z"
            precision = 9
        else:
            try:
                time_string, precision = node2.split("/")
                if time_string.startswith("^"):
                    time_string = time_string[1:]
                if time_string.startswith("+"):
                    time_string = time_string[1:]
                precision = int(precision)
            except:
                return None
        if not is_qualifier_edge:
            temp_time_dict = {
                "mainsnak": {
                    "snaktype": "value",
                    "property": prop,
                    "hash": "",
                    "datavalue": {
                        "value": {
                            "time": time_string,
                            "timezone": 0,
                            "before": 0,
                            "after": 0,
                            "precision": precision,
                            "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
                        },
                        "type": "time"
                    },
                    "datatype": "time"
                },
                "type": "statement",
                "id": node1 + prop + node2,
                "rank": rank,  # TODO
                "references": [],
                "qualifiers": {},
                "qualifiers-order": []
            }
        else:
            temp_time_dict = {
                "snaktype": "value",
                "property": prop,
                "hash": "",
                "datavalue": {
                    "value": {
                        "time": time_string,
                        "timezone": 0,
                        "before": 0,
                        "after": 0,
                        "precision": precision,
                        "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
                    },
                    "type": "time"
                },
                "datatype": "time"
            }
        return temp_time_dict

    def update_misc_json_dict_coordinate(self, node1: str, prop: str, node2: str, rank: str, is_qualifier_edge: bool):
        try:
            latitude, longitude = node2[1:].split("/")
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            return None
        if not is_qualifier_edge:
            temp_coordinate_dict = {
                "mainsnak": {
                    "snaktype": "value",
                    "property": prop,
                    "hash": "",
                    "datavalue": {
                        "value": {
                            "latitude": latitude,
                            "longitude": longitude,
                            "altitude": None,
                            "precision": 0.01,  # TODO
                            "globe": "http://www.wikidata.org/entity/Q2"
                        },
                        "type": "globecoordinate"
                    },
                    "datatype": "globecoordinate"
                },
                "type": "statement",
                "id": node1 + prop + node2,
                "rank": rank,
                "references": [],
                "qualifiers": {},
                "qualifiers-order": []
            }
        else:
            temp_coordinate_dict = {
                "snaktype": "value",
                "property": prop,
                "hash": "",
                "datavalue": {
                    "value": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "altitude": None,
                        "precision": 0.01,  # TODO
                        "globe": "http://www.wikidata.org/entity/Q2"
                    },
                    "type": "globecoordinate"
                },
                "datatype": "globecoordinate"
            }
        return temp_coordinate_dict

    def update_misc_json_dict_quantity(self, node1: str, prop: str, node2: str, rank: str, is_qualifier_edge: bool):
        try:
            res = self.quantity_pattern.match(node2).groups()
            amount, lower_bound, upper_bound, unit = res
            amount = JsonGenerator.clean_number_string(amount)
            lower_bound = JsonGenerator.clean_number_string(lower_bound)
            upper_bound = JsonGenerator.clean_number_string(upper_bound)
            unit = "http://www.wikidata.org/entity/" + unit if unit != None else None
        except:
            return None
        if not is_qualifier_edge:
            temp_quantity_dict = {
                "mainsnak": {
                    "snaktype": "value",
                    "property": prop,
                    "hash": "",
                    "datavalue": {
                        "value": {
                            "amount": amount,
                            "unit": unit,
                            "lowerBound": lower_bound,
                            "UpperBound": upper_bound
                        },
                        "type": "quantity"
                    },
                    "datatype": "quantity"
                },
                "type": "statement",
                "id": node1 + prop + node2,
                "rank": rank,
                "references": [],
                "qualifiers": {},
                "qualifiers-order": []
            }
        else:
            temp_quantity_dict = {
                "snaktype": "value",
                "property": prop,
                "hash": "",
                "datavalue": {
                    "value": {
                        "amount": amount,
                        "unit": unit,
                        "lowerBound": lower_bound,
                        "UpperBound": upper_bound
                    },
                    "type": "quantity"
                },
                "datatype": "quantity"
            }
        return temp_quantity_dict

    def update_misc_json_dict_monolingualtext(self, node1: str, prop: str, node2: str, rank: str,
                                              is_qualifier_edge: bool):
        text_string, lang = JsonGenerator.process_text_string(node2)
        if not is_qualifier_edge:
            temp_mono_dict = {
                "mainsnak": {
                    "snaktype": "value",
                    "property": prop,
                    "hash": "",
                    "datavalue": {
                        "value": {
                            "text": text_string,
                            "language": lang
                        },
                        "type": "monolingualtext"
                    },
                    "datatype": "monolingualtext"
                },
                "type": "statement",
                "id": node1 + prop + node2,
                "rank": rank,
                "references": [],
                "qualifiers": {},
                "qualifiers-order": []
            }
        else:
            temp_mono_dict = {
                "snaktype": "value",
                "property": prop,
                "hash": "",
                "datavalue": {
                    "value": {
                        "text": text_string,
                        "language": lang
                    },
                    "type": "monolingualtext"
                },
                "datatype": "monolingualtext"
            }
        return temp_mono_dict

    def update_misc_json_dict_string(self, node1: str, prop: str, node2: str, rank: str, is_qualifier_edge: bool):
        string, lang = JsonGenerator.process_text_string(node2)
        if not is_qualifier_edge:
            temp_string_dict = {
                "mainsnak": {
                    "snaktype": "value",
                    "property": prop,
                    "hash": "",
                    "datavalue": {"value": string, "type": "string"},
                    "datatype": "string"
                },
                "type": "statement",
                "id": node1 + prop + node2,
                "rank": rank,
                "references": [],
                "qualifiers": {},
                "qualifiers-order": []
            }
        else:
            temp_string_dict = {
                "snaktype": "value",
                "property": prop,
                "hash": "",
                "datavalue": {"value": string, "type": "string"},
                "datatype": "string"
            }
        return temp_string_dict

    def update_misc_json_dict_external_id(self, node1: str, prop: str, node2: str, rank: str, is_qualifier_edge: bool):

        if not is_qualifier_edge:
            temp_e_id_dict = {"mainsnak": {
                "snaktype": "value",
                "property": prop,
                "hash": "",
                "datavalue": {"value": node2, "type": "string"},
                "datatype": "external-id"
            },
                "type": "statement",
                "id": node1 + prop + node2,
                "rank": rank,
                "references": [],
                "qualifiers": {},
                "qualifiers-order": []
            }
        else:
            temp_e_id_dict = {
                "snaktype": "value",
                "property": prop,
                "hash": "",
                "datavalue": {"value": node2, "type": "string"},
                "datatype": "external-id"
            }
        return temp_e_id_dict

    def update_misc_json_dict_url(self, node1: str, prop: str, node2: str, rank: str, is_qualifier_edge: bool):
        if not is_qualifier_edge:
            temp_url_dict = {
                "mainsnak": {
                    "snaktype": "value",
                    "property": prop,
                    "hash": "",
                    "datavalue": {
                        "value": node2,
                        "type": "string"
                    },
                    "datatype": "url"
                },
                "type": "statement",
                "id": node1 + prop + node2,
                "rank": rank,
                "references": [],
                "qualifiers": {},
                "qualifiers-order": []
            }
        else:
            temp_url_dict = {
                "snaktype": "value",
                "property": prop,
                "hash": "",
                "datavalue": {
                    "value": node2,
                    "type": "string"
                },
                "datatype": "url"
            }
        return temp_url_dict

    def read_prop_declaration(self, line_number: int, edge: str):
        node1, node2, prop, e_id = self.parse_edges(edge)
        if prop == "data_type":
            self.prop_types[node1] = self.datatype_mapping[node2.strip()]
        return

    def set_properties(self, prop_file: str):
        self.prop_types = {}
        if prop_file == "NONE":
            return
        with open(prop_file, "r") as fp:
            props = fp.readlines()
        for line in props[1:]:
            node1, _, node2, = line.split("\t")
            try:
                self.prop_types[node1] = self.datatype_mapping[node2.strip()]
            except:
                raise KGTKException(
                    "DataType {} of node {} is not supported.\n".format(
                        node2, node1
                    )
                )

    def set_json_dict(self):
        self.misc_json_dict = {}
        # self.label_json_dict = {}
        # self.info_json_dict = {}

    def serialize(self):
        '''
        serialize the dictionaries. 
        '''
        with open("{}{}.jsonl".format(self.output_prefix, self.file_num), "w") as fp:
            for key, value in self.misc_json_dict.items():
                json.dump({key: value}, fp)
                fp.write("\n")
        self.file_num += 1
        self.reset()

    def reset(self):
        self.set_json_dict()
        self.read_num_of_lines = 0
        self.to_append_statement_id = None
        self.to_append_statement = None
