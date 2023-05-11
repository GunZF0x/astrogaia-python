#!/usr/bin/python3

import argparse
import sys
import logging
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.gaia import Gaia
import astroquery.utils.tap.core as tapcore
from pwn import *
import shutil
from tabulate import tabulate
import random
import matplotlib.pyplot as plt
from astropy.coordinates.name_resolve import NameResolveError as ResolveError


# ANSI escape codes dictionary
colors = {
        "BLACK": '\033[30m',
        "RED": '\033[31m',
        "GREEN": '\033[32m',
        "BROWN": '\033[33m',
        "BLUE": '\033[34m',
        "PURPLE": '\033[35m',
        "CYAN": '\033[36m',
        "WHITE": '\033[37m',
        "GRAY": '\033[1;30m',
        "L_RED": '\033[1;31m',
        "L_GREEN": '\033[1;32m',
        "YELLOW": '\033[1;33m',
        "L_BLUE": '\033[1;34m',
        "PINK": '\033[1;35m',
        "L_CYAN": '\033[1;36m',
        "NC": '\033[0m'
        }
script_version = 'v1.0.0'

# Define simple characters
sb: str = f'{colors["L_CYAN"]}[*]{colors["NC"]}' # [*]
sb_v2: str = f'{colors["RED"]}[{colors["YELLOW"]}+{colors["RED"]}]{colors["NC"]}' # [*]
whitespaces: str = " "*(len(sb)+1) # '    '
warning: str = f'{colors["YELLOW"]}[{colors["RED"]}!{colors["YELLOW"]}]{colors["NC"]}' # [!]


# Get user flags
def parseArgs():
    """
    Get commands and flags provided by the user
    """
    # General description / contact info
    general_description = f"{colors['L_CYAN']}Gaia DR3 tool written in Python 💫{colors['NC']} -- "
    general_description += f"{colors['L_GREEN']}Contact: {colors['GREEN']}Francisco Carrasco Varela \
                             (ffcarrasco@uc.cl) ⭐{colors['NC']}"

    parser = argparse.ArgumentParser(description=f"{general_description}", epilog=f"example: {sys.argv[0]} extract")

    # Define commands
    commands = parser.add_subparsers(dest='command')

    ### 'extract' command
    str_extract_command: str = 'extract'
    extract_command = commands.add_parser(str_extract_command, help=f'{colors["RED"]}Different modes to extract data{colors["NC"]}', 
                    description=f'{colors["L_RED"]}Extract data from Gaia{colors["NC"]}', epilog=f"example: {sys.argv[0]} extract raw")
    parser_sub_extract = extract_command.add_subparsers(dest='subcommand', 
                                                        help=f"{colors['RED']}Select the source/method to extract data{colors['NC']}")

    # Sub-command extract - raw
    str_extract_subcommand_raw: str = 'raw'
    extract_raw_subcommand_help = f"{colors['L_RED']}Extract raw Gaia data directly from Archive{colors['NC']}"
    extract_subcommand_raw = parser_sub_extract.add_parser(str_extract_subcommand_raw, description=extract_raw_subcommand_help,
                                                           help=f"{colors['RED']}Extract raw Gaia data directly from Archive{colors['NC']}",
                                                           epilog=f"example: {sys.argv[0]} extract raw rectangle")
    # Sub-subcommand: extract - raw - cone
    extract_raw_cone_subsubcommand_help = f"{colors['RED']}Extract data in 'cone search' mode{colors['NC']}"
    parser_sub_extract_raw = extract_subcommand_raw.add_subparsers(dest='subsubcommand', help=f"{colors['RED']}Shape to extract data{colors['NC']}")

    str_extract_subcommand_raw_subsubcommand_cone = 'cone'
    str_extract_subcommand_raw_subsubcommand_cone_examples = rf'''examples: {sys.argv[0]} extract raw cone -n "47 Tuc" -r 2.1 {colors["GRAY"]}# Extract data for "47 Tucanae" or "NGC104"{colors["NC"]}
            {sys.argv[0]} extract raw cone -ra "210" -dec "-60" -r 1.2 -n "myObject" {colors["GRAY"]}# Use a custom name/object, buy you have to provide coords{colors["NC"]}

    '''
    epilog_str = rf'''examples: {sys.argv[0]} extract raw cone -n "47 Tuc" -r 2.1 {colors["GRAY"]}# Extract data for "47 Tucanae" or "NGC104"{colors["NC"]}
          {sys.argv[0]} extract raw cone -ra "210" -dec "-60" -r 1.2 -n "myObject" {colors["GRAY"]}# Use a custom name/object, but you have to provide coords{colors["NC"]}
'''
    extract_subcommand_raw_subsubcommand_cone = parser_sub_extract_raw.add_parser(str_extract_subcommand_raw_subsubcommand_cone,
                                                                          help=f"{colors['RED']}Extract data in 'cone search' mode{colors['NC']}",
                                                                          description=f"{colors['L_RED']}Extract data in 'code search' mode{colors['NC']}",
                                                                          epilog=epilog_str, formatter_class=argparse.RawTextHelpFormatter)
    extract_subcommand_raw_subsubcommand_cone.add_argument('-n', '--name', type=str, required=True,
                                                           help="Object name. Ideally how it is found in catalogs and no spaces. Examples: 'NGC104', 'NGC_6121', 'Omega_Cen', 'myObject'")
    extract_subcommand_raw_subsubcommand_cone.add_argument('-r', '--radii', type=float, required=True,
                                                           help="Radius to extract data. Default units: degrees")
    extract_subcommand_raw_subsubcommand_cone.add_argument('--right-ascension', type=str,
                                                           help="Right ascension J2000 coordinates center. Default units: degrees. Not required if you provide a name found in catalogs.")
    extract_subcommand_raw_subsubcommand_cone.add_argument('--declination', type=str,
                                                           help="Declination J2000 coordinates center. Default units: degrees. Not required if you provide a name found in catalogs.")
    extract_subcommand_raw_subsubcommand_cone.add_argument('-o', '--outfile', type=str,
                                                           help="Output filename to save data")
    extract_subcommand_raw_subsubcommand_cone.add_argument('-x', '--file-extension', type=str, default="dat",
                                                           help="Extension for the output file")

    # Sub-subcommand: extract - raw - rectangle
    str_extract_subcommand_raw_subsubcommand_rect = 'rectangle'
    extract_subcommand_raw_subsubcommand_rect_example = f"example: {sys.argv[0]} extract raw rectangle -ra '210' -dec '-60' -r 6.5"
    extract_subcommand_raw_subsubcommand_rect = parser_sub_extract_raw.add_parser(str_extract_subcommand_raw_subsubcommand_rect,
                                                                                  help=f"{colors['RED']}Extract data in 'rectangle search' mode{colors['NC']}",
                                                                                  description=f"{colors['L_RED']}Extract data in rectangle shape{colors['NC']}",
                                                                                  epilog=f"example: {sys.argv[0]} extract raw rectangle ")
    extract_subcommand_raw_subsubcommand_rect.add_argument('-f', '--file', help="some file")
    extract_subcommand_raw_subsubcommand_rect.add_argument('-o', '--out', help="output file")

    ### 'plot' command
    str_plot_command: str = 'plot'
    plot_command = commands.add_parser(str_plot_command, help=f"{colors['GREEN']}Plot data{colors['NC']}")

    # Sub-command plot -> raw -- Plot data without any filter
    parser_subcommand_plot = plot_command.add_subparsers(dest='subcommand', help="Different modes to plot Gaia data")

    str_plot_subcommand_raw: str = 'raw'
    plot_subcommand_raw = parser_subcommand_plot.add_parser(str_plot_subcommand_raw,
                                                            help='Plot data directly extracted from Gaia Archive',
                                                            description=f'{colors["L_RED"]}Plot data directly extracted from Gaia Archive{colors["NC"]}')
    plot_subcommand_raw.add_argument('-n', '--name', help="Set a object name for the sample. Example: 'NGC104', 'my_sample'")
    plot_subcommand_raw.add_argument('-ra', "--right-ascension", help="Right Ascension (J2000) for the center of data")
    plot_subcommand_raw.add_argument('-dec', "--declination", help="Declination (J2000) for the center of data")
    plot_subcommand_raw.add_argument('-r', "--radii", help="Radius for the data centered in (RA, DEC) flags in arcmin")
    plot_subcommand_raw.add_argument('--ra-units', default="degree", type=str,  
                                      help="Specify the units to use based on 'astropy' (default: degree). Options: {deg, }")
    
    # Sub-command plot -> filter -- Plot data filtered
    str_plot_subcommand_filter : str = "from-file"
    plot_subcommand_filter = parser_subcommand_plot.add_parser(str_plot_subcommand_filter, 
                                                               help=f"Plot data from a file containing Gaia data")
    plot_subcommand_filter.add_argument("-n", "--name", help="Set a object name for the sample. Example: 'NGC104', 'my_sample'")


    ### 'show-gaia-content' command
    str_show_content_command: str = 'show-gaia-content'
    show_content_command =  commands.add_parser(str_show_content_command, 
                                                help=f"{colors['BROWN']}Show the type of content that different Gaia Releases can provide{colors['NC']}")
    show_content_command.add_argument('-r', '--gaia-release', default='gdr3',
                                      help="Select the Gaia Data Release you want to display what type of data contains. \
                                            Valid options: {gdr3, gaiadr3, g3dr3, gaia3dr3, gdr2, gaiadr2}")
    show_content_command.add_argument('-t', '--table-format', default='grid', 
                                      help="Table display format (default='grid'). To check all formats available visit: https://pypi.org/project/tabulate/")
    
    # parse the command-line arguments
    args = parser.parse_args()

    return parser, args

# Check if Python version running is at least 3.10
def checkPythonVersion() -> None:
    """
    Since this script uses some functions defined only since Python 3.10, it is required to run. Otherwise it will throw an errors while running
    """
    if sys.version_info < (3,10):
        print("{colors['L_RED']}[!] This function requires Python 3.10 (or higher) to run{colors['NC']}")
        sys.exit(1)
    return


def checkUserHasProvidedArguments(parser_provided, args_provided, n_args_provided) -> None:
    """
    Display help messages if the user has not provided arguments to a command/subcommand
    """
    # If user has not provided a command
    if args_provided.command is None:
        parser_provided.parse_args(['-h'])

    # If user has not provided a subcommand  
    if args_provided.command == "extract" and args_provided.subcommand is None:
        parser_provided.parse_args(['extract', '-h'])

    
    # If user has not provided any argument for the subcommand
    if args_provided.command == "extract" and args_provided.subcommand == "raw" and n_args_provided == 3:
        parser_provided.parse_args(['extract', 'raw', '-h'])


    if args_provided.command == "extract" and args_provided.subcommand == "raw" and args_provided.subsubcommand=="rectangle" and n_args_provided == 4:
        parser_provided.parse_args(['extract', 'raw', 'rectangle', '-h'])

    if args_provided.command == "plot" and args_provided.subcommand is None:
        parser_provided.parse_args(['plot', '-h'])

    if args_provided.command == "plot" and args_provided.subcommand == "raw" and n_args_provided == 3:
        parser_provided.parse_args(['plot', 'raw', '-h'])

    if args_provided.command == "plot" and args_provided.subcommand == "from-file" and n_args_provided == 3:
        parser_provided.parse_args(['plot', 'from-file', '-h'])
            

def checkNameObjectProvidedByUser(name_object):
    """
    Checks if a user has provided a valid object name. For example, object name 'NGC104' is valid, '<NGC104>' is not. 
    Also, 'NGC 104' is converted to 'NGC_104' for future functions/usage
    """
    pattern = r'^[\w ]+$'
    name_to_test = name_object.replace(' ', '_')
    pass_test = bool(re.match(pattern, name_object))
    if pass_test:
        return name_to_test
    if not pass_test:
        print("{warning} You have provided an invalid name (which may contain invalid characters): '{name_object}'")
        sys.exit(1)


def printBanner() -> None:
    # Color 1
    rand_number = random.randint(31,36) 
    c = f'\033[1;{rand_number}m' # color
    sh = f'\033[{rand_number}m' # shadow
    nc = colors['NC'] # no color / reset color
    # Color 2
    rand_number2 = random.randint(31,36) 
    c2 = f'\033[1;{rand_number2}m' # color
    sh2 = f'\033[{rand_number2}m' # shadow

    banner = rf'''   {c}_____            __{nc}                  
 {c} /  {sh}_  {c}\   _______/  |________  ____{nc}  
{c} /  {sh}/_\  {c}\ /  ___/\   __\_  __ \/  {sh}_ {c}\{nc}  
{c}/    |    \\___ \  |  |  |  | \(  {sh}<_> {c}){nc} 
{c}\____|__  /____  > |__|  |__|   \____/{nc} 
{c}        \/     \/{nc}                      
{c2}      ________        __{nc}                   
{c2}     /  _____/_____  |__|____{nc}              
{c2}    /   \  ___\__  \ |  \__  \{nc}             
{c2}    \    \_\  \/ {sh2}__ {c2}\|  |/ {sh2}__ {c2}\_{nc}            
{c2}     \______  (____  /__(____  /{nc}           
{c2}            \/     \/        \/{nc} {colors['GRAY']} {script_version}{nc}
    '''
    print(banner)
    print(f"\n{' ' * 11}by {colors['L_CYAN']}Francisco Carrasco Varela{colors['NC']}")
    print(f"{' ' * 21}{colors['CYAN']}(ffcarrasco@uc.cl){colors['NC']}")
    return


def displaySections(text, color_chosen=colors['NC'], character='#'):
    """
    Displays a section based on the user option/command
    """
    # Get the user's terminal width and compute its half size
    terminal_width = shutil.get_terminal_size().columns
    total_width = terminal_width // 2
    text_width = len(text) + 2
    padding_width = (total_width - text_width) // 2
    left_padding_width = padding_width
    right_padding_width = padding_width
    # If the number of characters is odd, add 1 extra character to readjust the size
    if (total_width - text_width) % 2 == 1:
        right_padding_width += 1
    left_padding = character * left_padding_width
    right_padding = character * right_padding_width
    # Create the text to display
    centered_text = f"{left_padding} {color_chosen}{text}{colors['NC']} {right_padding}"
    border = character * total_width
    # Print the result
    print(f"\n{border}\n{centered_text}\n{border}\n")


def randomColor() -> str:
    """
    Select a random color for text
    """
    return f'\033[{random.randint(31,36)}m'


def randomChar() -> str:
    """
    Select a random character to be printed
    """
    char_list = ['#', '=', '+', '$', '@']
    # 80% to pick '#', 20% remaining distributed for other characters
    weight_list = [0.8, 0.05, 0.05, 0.05, 0.05]
    return random.choices(char_list, weights=weight_list,k=1)[0]



#######################
## show-gaia-content ##
#######################
def read_columns_in_gaia_table(output_list):
    """
    We saved each column separated by '|'. Now use that character to split every row into its respective columns
    """
    rows = []

    for line in output_list:
        col = []
        row = line.strip().split("|")
        for column in row:
            col.append(column.strip())
        rows.append(col)
    return rows


def create_table_elements(width_terminal, printable_data_rows_table):
    """
    Add colors to the table and sets their parts ready to be printed
    """
    # Headers for the table
    headers_table = ["Row", "Name" ,"Var Type", "Unit", "Description"]
    # Get the max length (the sum of them) for columns that are not the "Description column"
    max_length = 0
    extra_gap = 19
    table_to_show = [row for row in printable_data_rows_table]
    for col in printable_data_rows_table:
        new_length = len(col[0]) + len(col[1]) + len(col[2]) + len(col[3]) + extra_gap 
        if new_length > max_length:
            max_length = new_length
    # Max allowed length before 'wrapping' text
    max_allowed_length = width_terminal - max_length - extra_gap

    colors_headers_table = [f"{colors['L_CYAN']}Row{colors['NC']}",
                            f"{colors['PINK']}Name{colors['NC']}",
                            f"{colors['YELLOW']}Var Type{colors['NC']}",
                            f"{colors['L_RED']}Units{colors['NC']}",
                            f"{colors['L_GREEN']}Description{colors['NC']}"]
    # Create a table body containing ANSI escape codes so it will print in colors
    colors_row_table = []
    for column_value in printable_data_rows_table:
        color_column = []
        # 'Row' column
        color_column.append(f"{colors['CYAN']}{column_value[0]}{colors['NC']}")
        # 'Name' column
        color_column.append(f"{colors['PURPLE']}{column_value[1]}{colors['NC']}")
        # 'Var Type' column
        color_column.append(f"{colors['BROWN']}{column_value[2]}{colors['NC']}")
        # 'Unit' column
        color_column.append(f"{colors['RED']}{column_value[3]}{colors['NC']}")
        # 'Description' column
        color_column.append(f"{colors['GREEN']}{column_value[4]}{colors['NC']}")
        colors_row_table.append(color_column)
    return colors_headers_table, colors_row_table, max_allowed_length


def print_table(body_table, headers_table, max_allowed_length, table_format):
    """
    Print the final table/result
    """
    print()
    print(tabulate(body_table, 
          headers=headers_table, tablefmt=table_format, 
          maxcolwidths=[None, None, None, None, max_allowed_length]))

def select_gaia_astroquery_service(service_requested: str) -> str:
    """
    Check the service the user wants to use
    """
    service_requested = service_requested.lower()
    if 'gaiadr3' in service_requested or 'gdr3' in service_requested:
        service = 'gaiadr3.gaia_source'
    elif 'gaiaedr3' in service_requested or 'gedr3' in service_requested:
        service = 'gaiaedr3.gaia_source'
    elif 'gaiadr2' in service_requested or 'gdr2' in service_requested:
        service = 'gaiadr2.gaia_source'
    else:
        print(f"The service you provided is not valid ('{service_requested}'). Using 'GaiaDR3' (default)...")
        service = 'gaiadr3.gaia_source'
    return service
    

def get_data_via_astroquery(input_service, input_ra, input_dec, input_radius, 
                            coords_units, radius_units, input_rows):
    """
    Get data applying a query to Astroquery
    """
    ### Get data via Astroquery
    Gaia.MAIN_GAIA_TABLE = input_service 
    Gaia.ROW_LIMIT = input_rows 
    p = log.progress(f'{colors["L_GREEN"]}Requesting data')
    logging.getLogger('astroquery').setLevel(logging.WARNING)

    # Make request to the service
    try:
        p.status(f"{colors['PURPLE']}Querying table for '{input_service.replace('.gaia_source', '')}' service...{colors['NC']}")
        coord = SkyCoord(ra=input_ra, dec=input_dec, unit=(coords_units, coords_units), frame='icrs')
        radius = u.Quantity(input_radius, radius_units)
        j = Gaia.cone_search_async(coord, radius)
        logging.getLogger('astroquery').setLevel(logging.INFO)
    except:
        p.failure(f"{colors['RED']}Error while requesting data. Check your internet connection is stable and retry...{colors['NC']}")
        sys.exit(1)

    p.success(f"{colors['L_GREEN']}Data obtained!{colors['NC']}")
    # Get the final data to display its columns as a table
    r = j.get_results()
    return r 
    

def get_content_table_to_display(data):
    """
    Get the content obtained via Astroquery and set it into a table-readable format, replacing some invalid/null values
    """
    output = ""
    output_list = []
    # Clean the data
    for j in range(0, len(data.colnames)):
        prop = data.colnames[j]
        # Set a value for 'unknown'/not set units
        if data[prop].info.unit == None:
            data[prop].info.unit = "-"
        # Clean '{\rm}', '$' and '}' characters from output
        if isinstance(data[prop].info.description, str):
            data[prop].info.description = data[prop].info.description.replace('$', '').replace('{\\rm','').replace("}",'')
        # If no description is provided, say it
        if isinstance(data[prop].info.description, type(None)):
            data[prop].info.description = "No description provided"
        
        output_list.append(f'{j+1} | {data[prop].info.name} | {data[prop].info.dtype} | {data[prop].info.unit} | {data[prop].info.description}')
    return output_list


def showGaiaContent(args) -> None:
    """
    Get columns to display for GaiaDR3, GaiaEDR3 or GaiaDR2
    """
    displaySections('show-gaia-content', randomColor(), randomChar())
    # Get arguments
    service_requested = args.gaia_release
    table_format = args.table_format
    # Get which service the user wants to use
    service = select_gaia_astroquery_service(service_requested)
    # Get an example data
    data = get_data_via_astroquery(service, 280, -60, 1.0, u.degree, u.deg, 1)
    # Get the data into a table format
    output_list = get_content_table_to_display(data)
    # To display the table first we need to get terminal width
    width = shutil.get_terminal_size()[0]
    # Get the data for the table (an array where every element is a row of the table)
    printable_data_table = read_columns_in_gaia_table(output_list)
    # Create table body that will be printed
    headers_table, body_table, max_allowed_length = create_table_elements(width, printable_data_table)
    # Print the obtained table
    print_table(body_table, headers_table, max_allowed_length, table_format)


####################
##### extract ######
####################

def get_object_coordinates(object_name):
    """
    Get the coordinates using service from Strasbourg astronomical Data Center (http://cdsweb.u-strasbg.fr)
    """

    p = log.progress(f"{colors['L_GREEN']}Object coordinates{colors['NC']}")
    try:
        p.status(f"{colors['GREEN']}Attempting to extract coordinates for your object...{colors['NC']}")
        # Use the SkyCoord.from_name() function to get the coordinates
        object_coord = SkyCoord.from_name(object_name)
        found_object = True

    except ResolveError:
        p.failure(f"{colors['RED']}Could not find coordinates for object '{object_name}'{colors['NC']}")
        found_object = False
        return None, found_object
    p.success("Coords extracted!")

    return object_coord, found_object


def decide_coords(args):
    """
    Based if the object provided by the user was found or not, decide what coordinates the program will use
    """
    object_coordinates, found_object = get_object_coordinates(args.name)
    if found_object:
        return object_coordinates.ra, object_coordinates.dec
    if not found_object:
        # Check if the user has provided parameters so we can extract the coordinates manually
        if args.right_ascension is None:
            print(f"{warning}{colors['RED']} Invalid object name ('{args.name}') and Right Ascension not provided ('--right-ascension')")
            sys.exit(1)
        if args.declination is None:
            print(f"{warning}{colors['RED']} Invalid object name ('{args.name}') and Declination not provided ('--declination')")
            sys.exit(1)
        # If the user has provided coordinates, use them

            




def extractCommand(args):
    # 'raw' subcommand
    if args.subcommand == "raw":
        # 'cone' subcommand
        if args.subsubcommand == "cone":
            RA, DEC = decide_coords(args)


####################
####### plot #######
####################

def plot_rawSubcommand(args):
    return
    

def plotCommand(args) -> None:
    """
    Plot data
    """
    if args.subcommand == 'raw':
        pass
    return

def main() -> None:
    # Parse the command-line arguments/get flags and their values provided by the user
    parser, args = parseArgs()

    # Check that user has provided non-empty arguments, otherwise print help message
    checkUserHasProvidedArguments(parser, args, len(sys.argv))

    printBanner()

    # Run 'show-gaia-content' command
    if args.command == 'show-gaia-content':
        showGaiaContent(args)

    # Run 'extract' command
    if args.command == 'extract':
        # Check if the user is using Python3.10 or higher, which is required for this function
        checkPythonVersion()
        extractCommand(args)


    if args.command == 'plot':
        plotCommand(args)
        

if __name__ == "__main__":
    main()
