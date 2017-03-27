# Copyright 2015, EMC, Inc.

# copyright text for generated files
COPYRIGHT_TEXT = '# Copyright 2015, EMC, Inc.'

"""
:mod:`onserve.schemas.redfish2restplus
=============================================================
.. module:: onserve.schemas.redfish2restplus
  :platform: (Ubuntu)Linux, Mac OS X, OnRack
  :synopsis:

Redfish2Restplus

assists in converting redfish schema definitions into restplus models.

usage example:

   from redfish2restplus import generate_restplus

   # redfish2restplus directories
   redfish_dir = 'redfish_1_0_0/json-schema'
   overlay_dir = 'redfish_1_0_0/json-overlay'
   model_path = 'redfish_1_0_0/models/model.py'

   # load redfish stock schema
   generate_restplus(redfish_dir, overlay_dir, model_path)

   anyOf compositions require a selection to be made in the
   overlay.  this is done via the 'select' keyword.

assumptions:
    - directories for schemas and models must already exist.
    - directories for schemas and models are relative to the cwd
"""

import json
import os
import string
import re
from copy import deepcopy
from toposort import toposort_flatten

# pylint doesn't like some constant names and method names (too long). pylint: disable=invalid-name
# pylint doesn't like use of builtin 'map' function. pylint: disable=bad-builtin
# static methods and docstrings are troublesome. pylint: disable=no-self-use

def generate_restplus(redfish_dir, overlay_dir_list, model_path):
    """
    A controller method that generates a restplus-based model definition
    :param redfish_dir: location of stock redfish schema files
    :param overlay_dir_list: list of schema overlay directories
    :param model_path: file path to write out models
    :return:
    """

    # load redfish stock schema
    redfish_schema = Redfish2Restplus(redfish_dir)
    redfish_schema.load()

    # load overlay
    for overlay_dir in overlay_dir_list:
        overlay_schema = Redfish2Restplus(overlay_dir)
        overlay_schema.load()
        # apply overlay to stock schema
        redfish_schema.overlay(overlay_schema)

    # build dependencies, enumerations and objects
    redfish_schema.finalize()

    # write restplus models
    redfish_schema.emit_schema(model_path)


_atomic_types = ['boolean', 'integer', 'number', 'string', 'null']

_primitive_types = _atomic_types + ['array', 'object']

_schema_keys = ['allOf', 'id', 'properties', 'definitions', '$schema', 'type', 'skip', 'title',
                'description', 'longDescription', 'additionalProperties', 'required',
                'copyright', '$ref']

_def_keys = ['additionalProperties', 'anyOf', 'description', 'enum', 'enumDescriptions',
             'format', 'items', 'longDescription', 'maximum', 'minimum', 'pattern',
             'patternProperties', 'properties', 'readonly', 'required', 'requiredOnCreate',
             'type']

_prop_keys = ['$ref', 'additionalProperties', 'description', 'enum', 'format', 'items',
              'longDescription', 'maximum', 'minimum', 'pattern', 'patternProperties',
              'properties', 'readonly', 'skip', 'type']

_ignored_in_modelpath_keys = ['definitions', 'properties', 'patternProperties']

_type_map = {'string': 'String', 'number': 'Float', 'boolean': 'Boolean',
             'array': 'List', 'object': 'Nested'}


class Redfish2Restplus(object):
    """
    Class that implements the conversion from redfish to restplus

    There is an implicit ordering to how the methods within this class are used.
    Should be used as follows:

    __init__()
    load()
    overlay()  (optional)
    finalize()
    emit_schema()

    There are no real safeguards on this ordering as of now.  So, its recommended that
    folks make use of the generate_restplus() method to handle the details.
    """
    def __init__(self, schema_dir):
        self.json_dict = dict()
        self._schema_dir = schema_dir
        self._def_dict = dict()
        self._ref_dict = dict()
        self._ordered_dependency_list = list()

    def load(self):
        """
        loads all json-formatted schema files found in schema_dir skipping any that are found
        to be unsupported
        :return: N/A
        """
        for fname in os.listdir(self._schema_dir):

            fpath = os.path.join(self._schema_dir, fname)

            if fpath.endswith('.json'):
                with open(fpath, 'r') as file_handle:

                    try:
                        json_dict = json.load(file_handle)
                    except ValueError:
                        print 'skipping {0}, badly formatted json'.format(fpath)
                        continue

                    # skip if specifically directed to
                    if 'skip' in json_dict:
                        print '{0} skipped'.format(fpath)
                        continue

                    # skip if schema is not supported
                    if not self.__supported_schema(json_dict):
                        print '{0} unsupported'.format(fpath)
                        continue

                    self.json_dict[fname] = json_dict

    def overlay(self, overlay):
        self.json_dict = self.__make_overlay(self.json_dict, overlay.json_dict)

    def __make_overlay(self, target_dict, overlay_dict):
        """
        overlay the 'overlay' schema on top of the current object(preferring values from the overlay)
        Note: the contents of the invoking object will be modified.  'overlay' itself won't be changed.
        :param target_dict: target dictionary
        :param overlay_dict: overlay dictionary
        :return: N/A
        """
        for key, value in overlay_dict.iteritems():
            if key in target_dict and isinstance(target_dict[key], dict):
                self.__make_overlay(target_dict[key], value)
            else:
                target_dict[key] = deepcopy(value)
        return target_dict

    def finalize(self):
        """
        complete necessary processing on complete schema, (dependencies, enumerations, model names)
        :return: N/A
        """
        self.__make_restplus()
        self.__make_reference_dict()
        self.__make_anyof_mappings()
        self.__make_dependencies()
        self.__order_dependency_list()

    def emit_schema(self, model_py_path):
        """
        writes out restplus models in one file.
        :param model_py_path: python file path to write out schema to
        :return: N/A
        """
        with open(model_py_path, 'w') as f_obj:

            # emit banner text
            self.__emit_banner_text(f_obj)
            f_obj.write('\n')

            # emit start of namespace
            self.__emit_flaskrestplus_namespace_begin(f_obj)

            # emit enumeration block
            self.__emit_enumerations(f_obj)

            # emit start of locals
            self.__emit_flaskrestplus_start_record(f_obj)
            f_obj.write('\n')

            for def_name in self._ordered_dependency_list:

                def_obj = self._def_dict[def_name]

                if def_obj.type == 'enum' or def_obj.type == 'anyOf':
                    # enum and anyOf are not written as models
                    continue

                self.__emit_model_definition(def_obj, f_obj)

                f_obj.write('\n')

            # emit end of namespace
            self.__emit_flaskrestplus_end_record(f_obj)

    def __supported_schema(self, input_dict):
        """
        test if the input_dict is invalid or should be skipped.
        :param input_dict: json dictionary to be tested
        :return: True if supported, False if not supported
        """
        if 'definitions' not in input_dict and 'properties' not in input_dict:
            return False
        return True

    def __emit_enumerations(self, f_obj):
        """
        write out enumeration definition block
        :param f_obj:
        :return:
        """
        f_obj.write('    # enumerations\n')
        for def_key in sorted(self._def_dict.keys()):
            def_val = self._def_dict[def_key]
            if def_val.type == 'enum':
                f_obj.write('    {0} = {1}\n'.format(def_key, def_val.def_dict['enum']))
                f_obj.write('\n')

    def __order_dependency_list(self):
        """
        considers the complete list of model dependencies and constructs an in-order name list
        that assures dependencies appear first.  toposort will fail if circular dependencies are
        found
        :return:
        """
        # contruct a dependency dictionary for use by toposort
        toposort_dict = dict()

        for def_key, def_val in self._def_dict.items():
            toposort_dict[def_key] = def_val.dependency_set

        # store a single list of ordered model names
        self._ordered_dependency_list = list(toposort_flatten(toposort_dict))

    def __construct_definitions(self, json_file, input_json):
        """
        constructs _Definition objects and store as def_dict
        :param json_file: originating json file name
        :param input_json: json block to consider
        :return:
        """
        if 'definitions' in input_json:
            for def_key, def_val in input_json['definitions'].items():
                self.__construct_properties(json_file, def_key, def_val)

    def __construct_properties(self, json_file, def_key, def_dict):
        """
        recursively searches for property and enum blocks.  a _Property
        or _Definition block is then generated and dependencies are noted.
        :param json_file: json block to consider
        :param def_key: definition context key
        :param def_dict: json block associated with def_key
        :return:
        """
        if 'properties' in def_dict:
            # create _Definition
            def_obj = self._Definition(json_file, def_key, def_dict)
            self._def_dict[def_obj.def_key] = def_obj
            for prop_key, prop_val in def_dict['properties'].items():
                if 'skip' in prop_val:
                    continue
                def_key_name = '{0}_{1}'.format(def_key, prop_key)
                self.__construct_properties(json_file, def_key_name, prop_val)
                prop_obj = self._Property(def_obj, prop_key, prop_val)
                def_obj.prop_dict[prop_obj.full_prop_name] = prop_obj
        elif 'anyOf' in def_dict:
            def_obj = self._Definition(json_file, def_key, def_dict)
            self._def_dict[def_obj.def_key] = def_obj
        elif 'enum' in def_dict:
            def_obj = self._Definition(json_file, def_key, def_dict)
            self._def_dict[def_obj.def_key] = def_obj

    def __make_restplus(self):
        """
        processes each schema file and stores enumerations, dependencies, and objects
        :return: N/A
        """
        # construct model names as dictionary
        for key, value in self.json_dict.items():
            self.__construct_definitions(key, value)

    def __emit_banner_text(self, f_obj):
        """
        emit banner text to warn against directly editing the restplus model
        :param f_obj: output file
        :return:
        """
        f_obj.write(COPYRIGHT_TEXT)
        f_obj.write('\n\n')
        f_obj.write('# **** generated by Redfish2Restplus\n')
        f_obj.write('# **** do not edit this file directly, edit json-overlay instead\n')

    def __emit_model_definition(self, def_obj, f_obj):
        """
        emit a model definition
        :param def_obj: _Definition object
        :param f_obj: output file
        :return:
        """
        self.__emit_flaskrestplus_model_begin(def_obj, f_obj)
        f_obj.write('\n')
        self.__emit_core_fields(def_obj, f_obj)
        f_obj.write('\n')
        self.__emit_flaskrestplus_namespace_model_begin(def_obj, f_obj)
        for _, prop_val in def_obj.prop_dict.items():
            self.__emit_flask_restplus_field(prop_val, f_obj)
        self.__emit_flaskrestplus_namespace_model_end(f_obj)

    def __emit_flaskrestplus_namespace_begin(self, f_obj):
        """
        emit namespace begin block
        :param f_obj: output file
        :return:
        """
        f_obj.write('# The model-names are supposed to look like this for use in the documentor.\n')
        f_obj.write('# pylint: disable=too-many-lines\n')
        f_obj.write('# pylint: disable=too-many-statements\n')
        f_obj.write('# pylint: disable=invalid-name,unused-variable,unused-argument\n')
        f_obj.write('# pylint: disable=line-too-long\n')
        f_obj.write('# pylint: disable=bad-continuation\n')
        f_obj.write('# pylint: disable=unused-import\n')
        f_obj.write('# pylint: disable=too-many-locals\n')
        f_obj.write('\n')
        f_obj.write('import flask_restplus as restplus\n')
        f_obj.write('\n')
        f_obj.write('def fake_import_driver(fake_importer, app_coord, namespace):\n')
        f_obj.write('\n')

    def __emit_flaskrestplus_start_record(self, f_obj):
        """
        emit start record
        :param f_obj:
        :return:
        """
        f_obj.write('    fake_importer.start_record(locals())\n')

    def __emit_flaskrestplus_end_record(self, f_obj):
        """
        emit end record
        :param f_obj:
        :return:
        """
        f_obj.write('    fake_importer.end_record(locals())\n')

    def __emit_core_fields(self, def_obj, f_obj):
        """
        given a _Definition object, emit the fields required for the model.
        :param def_obj: _Definition object
        :param f_obj: output file
        :return:
        """
        # write out atomic fields
        for _, prop_val in def_obj.prop_dict.items():
            if prop_val.type in _atomic_types:
                extra_params = list()
                if prop_val.attribute:
                    extra_params.append('attribute="{0}"'.format(prop_val.attribute))
                f_obj.write('    {0} = '.format(prop_val.full_prop_name))
                self.__emit_atomic_field(prop_val, extra_params, f_obj)
                f_obj.write('\n')

        # write out object fields
        for _, prop_val in def_obj.prop_dict.items():
            if prop_val.type == 'object':
                extra_params = list()
                if prop_val.attribute:
                    extra_params.append('attribute="{0}"'.format(prop_val.attribute))
                f_obj.write('    {0} = '.format(prop_val.full_prop_name))
                self.__emit_object_field(prop_val, extra_params, f_obj)
                f_obj.write('\n')

        # write out contained types for arrays
        for _, prop_val in def_obj.prop_dict.items():
            if prop_val.type == 'array':
                extra_params = list()
                if prop_val.attribute:
                    extra_params.append('attribute="{0}"'.format(prop_val.attribute))
                self.__emit_array_field(prop_val, extra_params, f_obj)
                f_obj.write('\n')

        # write out contained types for references
        for _, prop_val in def_obj.prop_dict.items():
            if prop_val.type == 'reference':
                extra_params = list()
                if prop_val.attribute:
                    extra_params.append('attribute="{0}"'.format(prop_val.attribute))
                self.__emit_reference_field(prop_val, extra_params, f_obj)
                f_obj.write('\n')

    def __emit_flaskrestplus_model_begin(self, def_obj, f_obj):
        """
        emit the start of a model definition
        :param model_name: name of model
        :param f_obj: output file
        :return:
        """
        f_obj.write('    #\n')
        f_obj.write('    # {0}\n'.format(def_obj.full_def_name))
        f_obj.write('    #\n')

    def __emit_flaskrestplus_namespace_model_begin(self, def_obj, f_obj):
        """
        emit the model namespace header
        :param def_obj: _Definition object
        :param f_obj: output file
        :return:
        """
        f_obj.write('    {0} = namespace.model("{0}",\n'.format(def_obj.full_def_name))
        f_obj.write('    {\n')

    def __emit_flaskrestplus_namespace_model_end(self, f_obj):
        """
        emit end to namespace
        :param f_obj: output file
        :return:
        """
        f_obj.write('    })\n')

    def __emit_flask_restplus_field(self, prop_obj, f_obj):
        """
        writes out the initial information required to begin a restplus field
        :param prop_obj: property object
        :param f_obj: output file
        :return:
        """
        f_obj.write('        "{0}": {1},\n'.format(prop_obj.prop_name, prop_obj.full_prop_name))

    def __emit_field_params(self, field_json, extra_list, f_obj):
        """
        given a json block, write out the flask restplus field parameters
        :param field_json: json block
        :param extra_list: a list of extra parameters to add
        :param f_obj: output file
        :return:
        """
        param_list = list()

        if isinstance(extra_list, list):
            param_list = extra_list

        if 'readonly' in field_json:
            param_list.append('readonly={0}'.format(field_json['readonly']))

        # create description
        if 'description' in field_json:
            param_list.append('description="{0}"'.format(field_json['description']))
        elif 'longDescription' in field_json:
            param_list.append('description="{0}"'.format(field_json['longDescription']))

        # default
        if 'default' in field_json:
            param_list.append('default="{0}"'.format(field_json['default']))

        # create example assignment
        if 'example' in field_json:
            param_list.append('example="{0}"'.format(field_json['example']))

        param_string = ',\n            '.join(map(str, param_list))
        f_obj.write('            {0})'.format(param_string))

    def __emit_object_field(self, prop_obj, extra_list, f_obj):
        """
        emit object blocks.  these translate to Nested restplus blocks
        :param prop_obj: _Property object
        :param extra_list: a list of parameter additions
        :param f_obj: output file
        :return:
        """
        prop_json = prop_obj.prop_dict
        assert 'type' in prop_json
        prop_type = _parse_type(prop_json['type'])
        assert prop_type == 'object'

        f_obj.write('restplus.fields.Nested({0},\n'.format(prop_obj.full_prop_name))
        self.__emit_field_params(prop_json, extra_list, f_obj)

    def __emit_atomic_field(self, prop_obj, extra_list, f_obj):
        """
        emit atomic fields (string, number, boolean, etc)
        :param prop_obj: _Property object
        :param extra_list: a list of parameter additions
        :param f_obj: output file
        :return:
        """
        prop_json = prop_obj.prop_dict
        assert 'type' in prop_json
        prop_type = _parse_type(prop_json['type'])
        assert prop_type in _atomic_types

        f_obj.write('restplus.fields.{0}(\n'.format(_type_map[prop_type]))
        self.__emit_field_params(prop_json, extra_list, f_obj)

    def __emit_reference_field(self, prop_obj, extra_list, f_obj):
        """
        emit a reference field ($ref), results in a either a Nested restplus field
        or atomic restplus field based on object that is referred to
        :param prop_obj: _Property object
        :param extra_list: a list of parameter additions
        :param f_obj: output file
        :return:
        """
        prop_json = prop_obj.prop_dict
        assert '$ref' in prop_json
        assert prop_obj.type == 'reference'

        ref = prop_obj.prop_dict['$ref']
        ref_name = self.__ref_name(ref)
        ref_json = self.__ref_json(ref)

        inner_name = 'inner_{0}'.format(prop_obj.full_prop_name)
        f_obj.write('    {0} = '.format(inner_name))

        if 'type' in ref_json:
            # reference to formal type
            ref_type = ref_json['type']
            if ref_type == 'object':
                f_obj.write('{0}\n'.format(ref_name))
            elif ref_type in _atomic_types:
                # a reference to an atomic type just results in an atomic type (no Nesting)
                inner_params = list()
                if prop_obj.attribute:
                    inner_params.append('attribute="{0}"'.format(prop_obj.attribute))
                if 'enum' in ref_json:
                    inner_params.append('enum={0}'.format(ref_name))
                    if 'enumDescriptions' in ref_json:
                        enumDescriptionString = ', '.join('{0}: {1}'.format(key, value) \
                            for key, value in ref_json['enumDescriptions'].items())
                        inner_params.append('description="{0}"'.format(enumDescriptionString))
                f_obj.write('restplus.fields.{0}(\n'.format(_type_map[ref_type]))
                self.__emit_field_params(ref_json, inner_params, f_obj)
                f_obj.write('\n')
                f_obj.write('    {0} = {1}\n'.format(prop_obj.full_prop_name, inner_name))
                return
            else:
                assert False, 'unexpected reference type {0} in {1}'.format(ref_type, prop_obj.def_key)
        else:
            assert False, 'unexpected reference format in {0}'.format(prop_obj.def_key)

        f_obj.write('    {0} = restplus.fields.Nested({1},\n'.format(
            prop_obj.full_prop_name, inner_name))
        self.__emit_field_params(prop_json, extra_list, f_obj)
        f_obj.write('\n')

    def __emit_array_field(self, prop_obj, extra_list, f_obj):
        """
        emit an array field.  Translated as either restplus List, Nested(as_list=True based
        on whether contained object is a field or model
        :param prop_obj: _Property object
        :param extra_list: a list of additional parameters
        :param f_obj: output file
        :return:
        """
        prop_json = prop_obj.prop_dict
        assert 'type' in prop_json
        assert prop_json['type'] == 'array'

        is_nested = False

        # write out inner type
        inner_name = 'inner_{0}'.format(prop_obj.full_prop_name)
        f_obj.write('    {0} = '.format(inner_name))

        if '$ref' in prop_obj.prop_dict['items']:
            # array of ref
            ref = prop_obj.prop_dict['items']['$ref']
            ref_name = self.__ref_name(ref)
            ref_json = self.__ref_json(ref)

            if 'type' in ref_json:
                ref_type = _parse_type(ref_json['type'])
                if ref_type == 'object':
                    is_nested = True
                    f_obj.write('{0}\n'.format(ref_name))
                elif ref_type in _atomic_types:
                    inner_params = list()
                    if prop_obj.attribute:
                        inner_params.append('attribute="{0}"'.format(prop_obj.attribute))
                    if 'enum' in ref_json:
                        inner_params.append('enum={0}'.format(ref_name))
                    f_obj.write('restplus.fields.{0}(\n'.format(_type_map[ref_type]))
                    self.__emit_field_params(prop_json, inner_params, f_obj)
                    f_obj.write('\n')
            else:
                assert False
        else:
            inner_type = _parse_type(prop_json['items']['type'])
            f_obj.write('restplus.fields.{0}(\n'.format(_type_map[inner_type]))
            self.__emit_field_params(prop_json, None, f_obj)
            f_obj.write('\n')

        if is_nested:
            # write out nested composition
            f_obj.write('    {0} = restplus.fields.Nested({1}, as_list=True,\n'.format(
                prop_obj.full_prop_name, inner_name))
            self.__emit_field_params(prop_json, extra_list, f_obj)
            f_obj.write('\n')
        else:
            # write out list composition
            f_obj.write('    {0} = restplus.fields.List({1},\n'.format(
                prop_obj.full_prop_name, inner_name))
            self.__emit_field_params(prop_json, extra_list, f_obj)
            f_obj.write('\n')

    def __make_anyof_mappings(self):
        """
        hunts through definitions looking for anyOf compositions.  satisfy the
        $ref through the use of the "select" keyword.
        :return:
        """
        for _, def_val in self._def_dict.items():
            for _, prop_obj in def_val.prop_dict.items():
                if prop_obj.type == 'array':
                    if '$ref' in prop_obj.prop_dict['items']:
                        ref = self.__map_ref_to_json(prop_obj.prop_dict['items']['$ref'], prop_obj.def_obj.def_file)
                        ref_json = ref['ref_json']
                        if 'anyOf' in ref_json:
                            prop_obj.prop_dict['items']['$ref'] = ref_json['select']
                elif '$ref' in prop_obj.prop_dict:
                    ref = self.__map_ref_to_json(prop_obj.prop_dict['$ref'], prop_obj.def_obj.def_file)
                    ref_json = ref['ref_json']
                    if 'anyOf' in ref_json:
                        prop_obj.prop_dict['$ref'] = ref_json['select']

    def __make_dependencies(self):
        """
        creates a set of dependencies of each object, array and reference
        :return:
        """
        for _, def_val in self._def_dict.items():
            for _, prop_val in def_val.prop_dict.items():
                if prop_val.type == 'object':
                    def_val.dependency_set |= {prop_val.full_prop_name}
                elif prop_val.type == 'array':
                    if '$ref' in prop_val.prop_dict['items']:
                        ref_name = self.__ref_name(prop_val.prop_dict['items']['$ref'])
                        def_val.dependency_set |= {ref_name}
                elif prop_val.type == 'reference':
                    if prop_val.ref_key in self._def_dict:
                        def_val.dependency_set |= {prop_val.ref_key}

    def __make_reference_dict(self, json_context=None, json_file=None):
        """
        creates a dictionary that is key'd with a '$ref' value and maps to a json block
        :param json_context: json context for recursive calls
        :param json_file: json file as base for local references
        :return:
        """
        if json_file == None:
            for key, value in self.json_dict.items():
                if 'redfish-schema' in key:
                    continue
                json_file = key
                json_context = value
                if '$ref' in json_context:
                    ref_name = json_context['$ref']
                    self._ref_dict[ref_name] = self.__map_ref_to_json(ref_name, json_file)
                self.__make_reference_dict(json_context, json_file)
        elif isinstance(json_context, dict):
            if 'anyOf' in json_context:
                # map anyOf based on select statement
                assert 'select' in json_context, 'anyOf is missing \'select\' statement'
                ref_name = json_context['select']
                self._ref_dict[ref_name] = self.__map_ref_to_json(ref_name, json_file)
            elif '$ref' in json_context:
                ref_name = json_context['$ref']
                self._ref_dict[ref_name] = self.__map_ref_to_json(ref_name, json_file)
            for key, value in json_context.items():
                self.__make_reference_dict(value, json_file)
        elif isinstance(json_context, list):
            for value in json_context:
                self.__make_reference_dict(value, json_file)

    def __map_ref_to_json(self, ref, json_file):
        """
        given a $ref value and the json_file name that contained
        it, return a dictionary containing the following:
             { "ref_name":   "python_name_for_reference"
               "ref_json":  "json block that this refers to"
             }
        :param ref: value of $ref
        :param json_file: json file as base for local references
        :return:
        """
        if ref.startswith('#/'):
            # local reference
            json_file = json_file
            ref_path = ref[len('#/'):]
        else:
            ref_split = ref.split('#/')
            ref_path = ref_split[1]
            json_file_path = ref_split[0]
            json_file_split = json_file_path.split('/')
            json_file = json_file_split[-1]

        ref_json = self.json_dict[json_file]

        # find the json block
        path_split = ref_path.split('/')
        for entry in path_split:
            ref_json = ref_json[entry]

        json_name = json_file.replace('.json', '')
        path_split.remove('definitions')
        ref_name = '_'.join(map(str, [json_name] + path_split))
        ref_name = _normalize_model_name(ref_name)

        return {"ref_name": ref_name, "ref_json": ref_json}

    def __ref_json(self, ref):
        return self._ref_dict[ref]['ref_json']

    def __ref_name(self, ref):
        return self._ref_dict[ref]['ref_name']

    class _Property(object):
        """
        container for storing properties
        """
        def __init__(self, def_obj, prop_name, prop_dict):

            self.def_obj = def_obj
            self.def_base = def_obj.def_base
            self.def_name = def_obj.def_name
            normal_prop_name = _normalize_model_name(prop_name)
            self.full_prop_name = '{0}_{1}_{2}'.format(self.def_base, self.def_name, normal_prop_name)

            self.prop_name = prop_name
            self.prop_dict = prop_dict

            self.required = False

            # store special attribute name if offending characters found
            if re.search('[@.]', prop_name):
                self.attribute = prop_name.replace('@', '')
                self.attribute = self.attribute.replace('.', '_')
            else:
                self.attribute = None

            # determine type
            if 'type' in prop_dict:
                self.type = _parse_type(prop_dict['type'])
                self.ref_name = None
            elif '$ref' in prop_dict:
                self.type = 'reference'
                if prop_dict['$ref'].startswith('#/definitions/'):
                    self.ref_base = self.def_base
                    ref_split = prop_dict['$ref'].split('#/definitions/')
                    self.ref_name = ref_split[1]
                else:
                    ref_split = prop_dict['$ref'].split('.json#/definitions/')
                    self.ref_base = ref_split[0].split('/')[-1]
                    self.ref_name = ref_split[1]
                self.ref_key = '{0}_{1}'.format(self.ref_base, self.ref_name)
                self.ref_key = _normalize_model_name(self.ref_key)

            # print 'constructed _PropertyField {0} of type {1}'.format(self.full_prop_name, self.type)

    class _Definition(object):
        """
        container for storing definitions
        """
        def __init__(self, json_file, def_name, def_dict):
            self.def_file = json_file
            self.def_base = json_file.replace('.json', '')
            self.def_base = self.def_base.replace('-', '_')
            self.def_base = self.def_base.replace('.', '_')
            self.def_name = def_name
            self.def_name = def_name.replace('.', '_')
            self.full_def_name = '{0}_{1}'.format(self.def_base, self.def_name)
            self.dependency_set = set()
            self.def_dict = def_dict
            self.prop_dict = dict()
            self.def_key = '{0}_{1}'.format(self.def_base, self.def_name)

            if 'type' in def_dict:
                self.type = _parse_type(def_dict['type'])
            elif '$ref' in def_dict:
                self.type = 'reference'
            if 'enum' in def_dict:
                self.type = 'enum'
            if 'anyOf' in def_dict:
                self.type = 'anyOf'

            # print 'constructed _Definition {0} of type {1}'.format(self.def_key, self.type)

        def add_dependency(self, dep_name):
            self.dependency_set |= {dep_name}

def _normalize_model_name(model_name):
    """
    normalize a model name to be suitable for use as a python symbol
    :param model_name: model name to be normalized
    :return: normalized model name as string
    """
    name_copy = string.replace(model_name, '.json', '')
    name_copy = string.replace(name_copy, '@', '')
    name_copy = string.replace(name_copy, '#', '')
    name_copy = string.replace(name_copy, '-', '_')
    return string.replace(name_copy, '.', '_')

def _parse_type(type_value):
    """
    convert a json schema type directive into a simple string.  json schema types can be:
        [ null, <type> ] of type <type> and can be nullable
        <type>, type
    where <type> is "string", "number", etc.
    :param type_value:
    :return: type_value
    """
    if isinstance(type_value, list):
        assert len(type_value) == 2
        assert 'null' in type_value
        type_list = list(type_value)
        type_list.remove('null')
        local_type_value = type_list[0]
    else:
        local_type_value = type_value
    return local_type_value
