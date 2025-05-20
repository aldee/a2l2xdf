import json
import xml.etree.ElementTree as ET
import argparse

def create_xdf_element(parent, tag, text=None, attributes=None):
    attributes_to_use = {}
    if attributes:
        processed_attributes = {}
        for k, v in attributes.items():
            if v is None:
                print(f"Warning: Attribute '{k}' for tag '{tag}' was None. Converting to empty string.")
                processed_attributes[k] = ""
            elif not isinstance(v, str):
                processed_attributes[k] = str(v)
            else:
                processed_attributes[k] = v
        attributes_to_use = processed_attributes
    
    if parent is None:
        element = ET.Element(tag, attributes_to_use)
    else:
        element = ET.SubElement(parent, tag, attributes_to_use)
    
    if text is not None:
        element.text = str(text)
    return element

def create_text_element(parent, tag, text, attributes=None):
    element = create_xdf_element(parent, tag, text=str(text), attributes=attributes)
    return element

def json_to_xdf(json_file, xdf_file, base_offset_hex):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found: {json_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in: {json_file}")
        return

    try:
        base_offset_int = int(base_offset_hex, 16)
    except ValueError:
        print(f"Error: Invalid hexadecimal format for BASEOFFSET: {base_offset_hex}")
        return

    xdfformat = create_xdf_element(None, "XDFFORMAT", attributes={"version": "1.80"})
    xdfheader = create_xdf_element(xdfformat, "XDFHEADER")
    create_text_element(xdfheader, "flags", "0x1")
    
    default_title_name = json_file.split('/')[-1].split('\\')[-1].split('.')[0]
    deftitle_from_json = data.get("filename", default_title_name) 
    create_text_element(xdfheader, "deftitle", str(deftitle_from_json))
    create_text_element(xdfheader, "description", f"Mappack for {deftitle_from_json} generated from JSON")
    create_xdf_element(xdfheader, "BASEOFFSET", attributes={"offset": str(base_offset_int), "subtract": "0"})
    create_xdf_element(xdfheader, "DEFAULTS",
                       attributes={"datasizeinbits": "8", "sigdigits": "4", "outputtype": "1", 
                                   "signed": "0", # Default signedness (can be overridden by mmedtypeflags)
                                   "lsbfirst": "1", "float": "0"})
    create_xdf_element(xdfformat, "REGION",
                       attributes={"type": "0xFFFFFFFF", "startaddress": "0x0", "size": "0x800000",
                                   "regioncolor": "0x0", "regionflags": "0x0", "name": "Binary",
                                   "desc": "Full Binary Region"})

    categories_map = {}
    category_index_counter = 0 
    map_groups_from_json = data.get("maps", [])

    if not map_groups_from_json:
        default_cat_name = "Generic"
        hex_cat_idx_str = "0x0" 
        categories_map[default_cat_name] = hex_cat_idx_str
        create_xdf_element(xdfformat, "CATEGORY", attributes={"index": hex_cat_idx_str, "name": default_cat_name})
    else:
        for i, group in enumerate(map_groups_from_json):
            category_name_val = group.get("name")
            processed_category_name = str(category_name_val).strip() if category_name_val is not None else ""
            
            if not processed_category_name:
                processed_category_name = f"Unnamed Category {i + 1}"
            
            if processed_category_name not in categories_map:
                hex_category_index_str = hex(category_index_counter) 
                categories_map[processed_category_name] = hex_category_index_str 
                
                create_xdf_element(xdfformat, "CATEGORY",
                                   attributes={"index": hex_category_index_str, 
                                               "name": processed_category_name})
                category_index_counter += 1
    
    for group_idx, maps_group in enumerate(map_groups_from_json):
        current_group_name_val = maps_group.get("name")
        processed_group_name_for_lookup = str(current_group_name_val).strip() if current_group_name_val is not None else ""

        if not processed_group_name_for_lookup:
            processed_group_name_for_lookup = f"Unnamed Category {group_idx + 1}"
        
        zero_based_hex_idx_str = categories_map.get(processed_group_name_for_lookup, "0x0") 
        
        try:
            zero_based_decimal_val = int(zero_based_hex_idx_str, 16)
            one_based_decimal_val_for_categorymem = zero_based_decimal_val + 1
            category_attr_for_table = str(one_based_decimal_val_for_categorymem)
        except ValueError:
            category_attr_for_table = "1" 

        for json_map in maps_group.get("maps", []):
            address = json_map.get("address")
            mmedaddress_hex = hex(address - base_offset_int) if address is not None else "0x0"

            xdftable = create_xdf_element(xdfformat, "XDFTABLE", attributes={"flags": "0x0", "uniqueid": mmedaddress_hex})
            
            map_name = json_map.get("name", "Unknown Map")
            create_text_element(xdftable, "title", str(map_name))

            table_description_val = json_map.get("map_id", map_name) 
            create_text_element(xdftable, "description", str(table_description_val))
            
            create_xdf_element(xdftable, "CATEGORYMEM", 
                               attributes={"index": "0", 
                                           "category": category_attr_for_table}) 

            create_xdf_axis(xdftable, "x", json_map.get("x", {}), base_offset_int, mmedaddress_hex)
            create_xdf_axis(xdftable, "y", json_map.get("y", {}), base_offset_int, mmedaddress_hex)
            create_xdf_axis_z(xdftable, "z", json_map, base_offset_int)

    tree = ET.ElementTree(xdfformat)
    ET.indent(tree, space="\t", level=0)
    tree.write(xdf_file, encoding='utf-8', xml_declaration=True)

def create_xdf_axis(axis_parent, axis_id_param, json_axis, base_offset_int, table_unique_id_hex):
    if not json_axis: 
        return
    
    address = json_axis.get("address")
    skip_bytes = json_axis.get("skip_bytes", 0)
    
    if address is not None:
        mmedaddress_val = address + skip_bytes - base_offset_int
        mmedaddress_hex = hex(mmedaddress_val)
        axis_unique_id = mmedaddress_hex
    else:
        mmedaddress_hex = "0x0"
        axis_unique_id = f"{table_unique_id_hex}_{axis_id_param}_axis"

    xdf_axis = create_xdf_element(axis_parent, "XDFAXIS", attributes={"id": axis_id_param, "uniqueid": axis_unique_id})
    
    _axis_id_val_from_json = json_axis.get("axis_id")
    axis_label_text = str(_axis_id_val_from_json).strip() if _axis_id_val_from_json is not None else ""
    if not axis_label_text: axis_label_text = f"Axis {axis_id_param.upper()}"
    create_text_element(xdf_axis, "title", axis_label_text)

    data_organization = json_axis.get("data_organization")
    mmedelementsizebits = 16 if data_organization == "LOHI" else 8
    
    element_default_bytes = mmedelementsizebits / 8.0
    stride_val = json_axis.get("stride", element_default_bytes)
    stride_bytes = float(stride_val) if stride_val is not None else element_default_bytes
    actual_stride_bits_for_storage = int(stride_bytes * 8)

    current_mmedtypeflags_val = 0x02 
    is_xy_signed = json_axis.get("signed", False) 
    if is_xy_signed:
        current_mmedtypeflags_val = current_mmedtypeflags_val | 0x01
    mmedtypeflags_xy_hex = hex(current_mmedtypeflags_val)

    embeddata_attribs = {
        "mmedelementsizebits": str(mmedelementsizebits),
        "mmedtypeflags": mmedtypeflags_xy_hex,
    }

    if address is not None:
        embeddata_attribs["mmedaddress"] = mmedaddress_hex
        create_xdf_element(xdf_axis, "embedinfo", attributes={"type": "1"})

    size = json_axis.get("size", 0)
    if axis_id_param == "x":
        embeddata_attribs["mmedcolcount"] = str(size)
        embeddata_attribs["mmedrowcount"] = "1"
        embeddata_attribs["mmedminorstridebits"] = str(actual_stride_bits_for_storage) if actual_stride_bits_for_storage > mmedelementsizebits else "0"
        embeddata_attribs["mmedmajorstridebits"] = "0"
    elif axis_id_param == "y":
        embeddata_attribs["mmedrowcount"] = str(size)
        embeddata_attribs["mmedcolcount"] = "1"
        embeddata_attribs["mmedmajorstridebits"] = str(actual_stride_bits_for_storage) if actual_stride_bits_for_storage > mmedelementsizebits else "0"
        embeddata_attribs["mmedminorstridebits"] = "0"

    if size > 0 :
        create_xdf_element(xdf_axis, "EMBEDDEDDATA", attributes=embeddata_attribs)

    create_text_element(xdf_axis, "indexcount", str(size))
    create_text_element(xdf_axis, "datatype", "1" if is_xy_signed else "0") # Example: 1 for signed, 0 for unsigned
    
    _units_val = json_axis.get("units")
    axis_units_label = str(_units_val).strip() if _units_val is not None else axis_label_text
    if not axis_units_label: axis_units_label = f"{axis_id_param}-units"
    create_text_element(xdf_axis, "unittype", "0", attributes={"label": axis_units_label})

    create_xdf_element(xdf_axis, "DALINK", attributes={"index": "0"})

    factor = json_axis.get("factor", 1.0)
    addition = json_axis.get("addition", 0.0)
    math_equation = f"(( {float(factor)} * X) + {float(addition)} )"
    math_element = create_xdf_element(xdf_axis, "MATH", attributes={"equation": math_equation})
    create_xdf_element(math_element, "VAR", attributes={"id": "X"})

    decimalpl = json_axis.get("precision", 2)
    
    min_val_str = str(json_axis.get("min_val", "0.0")) # Default, consider signedness
    max_val_default_xy = "0.0" 
    if is_xy_signed and mmedelementsizebits == 8:
        max_val_default_xy = "127.0"
        if min_val_str == "0.0" and json_axis.get("min_val") is None: min_val_str = "-128.0"
    elif is_xy_signed and mmedelementsizebits == 16:
        max_val_default_xy = "32767.0"
        if min_val_str == "0.0" and json_axis.get("min_val") is None: min_val_str = "-32768.0"
    elif mmedelementsizebits == 8: # Unsigned
        max_val_default_xy = "255.0"
    else: # 16-bit unsigned
        max_val_default_xy = "65535.0"
    max_val_str = str(json_axis.get("max_val", max_val_default_xy ))

    create_text_element(xdf_axis, "decimalpl", str(decimalpl))
    create_text_element(xdf_axis, "min", min_val_str)
    create_text_element(xdf_axis, "max", max_val_str)

def create_xdf_axis_z(axis_parent, axis_id_param, json_map, base_offset_int):
    xdf_axis = create_xdf_element(axis_parent, "XDFAXIS", attributes={"id": axis_id_param})
    map_name_for_z_title_val = json_map.get("name")
    map_name_for_z_title = str(map_name_for_z_title_val).strip() if map_name_for_z_title_val is not None else "Table Data"
    if not map_name_for_z_title : map_name_for_z_title = "Table Data"
    create_text_element(xdf_axis, "title", map_name_for_z_title)

    address = json_map.get("address")
    mmedaddress_hex = hex(address - base_offset_int) if address is not None else "0x0"

    data_organization = json_map.get("data_organization")
    mmedelementsizebits_Z = 16 if data_organization == "LOHI" else 8

    width = json_map.get("width", 1)
    height = json_map.get("height", 1)
    
    element_byte_size_Z = mmedelementsizebits_Z / 8.0
    stride_val_Z = json_map.get("stride", element_byte_size_Z)
    stride_bytes_Z = float(stride_val_Z) if stride_val_Z is not None else element_byte_size_Z
    line_skip_bytes = json_map.get("line_skip_bytes", 0)

    actual_element_stride_bits_Z = int(stride_bytes_Z * 8)
    mmedminorstridebits_val = str(actual_element_stride_bits_Z) if actual_element_stride_bits_Z > mmedelementsizebits_Z else "0"
    
    mmedmajorstridebits_val = "0"
    if line_skip_bytes > 0:
        bytes_for_data_in_row = width * stride_bytes_Z
        total_bytes_for_row_with_skip = bytes_for_data_in_row + line_skip_bytes
        mmedmajorstridebits_val = str(int(total_bytes_for_row_with_skip * 8))
    elif actual_element_stride_bits_Z > mmedelementsizebits_Z and line_skip_bytes == 0:
         if width > 1 : 
            mmedmajorstridebits_val = str(int(width * actual_element_stride_bits_Z))

    current_mmedtypeflags_val = 0x02
    is_z_signed = json_map.get("z_signed", False) 
    if is_z_signed:
        current_mmedtypeflags_val = current_mmedtypeflags_val | 0x01
    mmedtypeflags_hex = hex(current_mmedtypeflags_val)

    embed_data_attrs = {
        "mmedaddress": mmedaddress_hex,
        "mmedelementsizebits": str(mmedelementsizebits_Z),
        "mmedmajorstridebits": mmedmajorstridebits_val,
        "mmedminorstridebits": mmedminorstridebits_val,
        "mmedtypeflags": mmedtypeflags_hex,
        "mmedcolcount": str(width),
        "mmedrowcount": str(height)
    }
    create_xdf_element(xdf_axis, "EMBEDDEDDATA", attributes=embed_data_attrs)

    factor = json_map.get("factor", 1.0)
    addition = json_map.get("addition", 0.0)
    math_equation = f"(( {float(factor)} * X) + {float(addition)} )"
    math_element = create_xdf_element(xdf_axis, "MATH", attributes={"equation": math_equation})
    create_xdf_element(math_element, "VAR", attributes={"id": "X"})

    decimalpl = json_map.get("precision", 2)
    
    _units_z_val = json_map.get("z_units")
    units_z = str(_units_z_val).strip() if _units_z_val is not None else "Value"
    if not units_z: units_z = "Value"

    # Min/Max for Z-axis display after math
    min_val_z_str = str(json_map.get("z_min_val", "0.0")) # Default to 0.0
    max_val_z_default = "0.0" # Placeholder to be determined

    if is_z_signed:
        if mmedelementsizebits_Z == 8:
            max_val_z_default = "127.0" # Example, based on factor/offset these could vary widely
            if json_map.get("z_min_val") is None : min_val_z_str = "-128.0"
        elif mmedelementsizebits_Z == 16:
            max_val_z_default = "32767.0"
            if json_map.get("z_min_val") is None : min_val_z_str = "-32768.0"
    else: # Unsigned
        max_val_z_default = "255.0" if mmedelementsizebits_Z == 8 else "65535.0"
    
    max_val_z_str = str(json_map.get("z_max_val", max_val_z_default))


    create_text_element(xdf_axis, "decimalpl", str(decimalpl))
    create_text_element(xdf_axis, "units", units_z)
    create_text_element(xdf_axis, "min", min_val_z_str) 
    create_text_element(xdf_axis, "max", max_val_z_str) 
    create_text_element(xdf_axis, "outputtype", "1")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert JSON to XDF for ECU mappacks.")
    parser.add_argument("json_file", help="Path to the input JSON file.")
    parser.add_argument("xdf_file", help="Path to the output XDF file.")
    parser.add_argument("--baseoffset", help="Hexadecimal value for the BASEOFFSET (e.g., 0x200000)", default="0x0")
    args = parser.parse_args()

    json_to_xdf(args.json_file, args.xdf_file, args.baseoffset)
    print(f"Conversion complete. XDF file created: {args.xdf_file}")