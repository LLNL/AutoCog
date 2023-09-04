
from parsimonious.grammar import Grammar

grammar = Grammar(r"""
program          = declaration__* WS
declaration__    = WS declaration
declaration      = def_decl / arg_decl / format_decl / struct_decl / prompt_decl / flow_block / annot_block

def_decl         = DEFINE WS identifier WS initializer WS SC
arg_decl         = ARGUMENT WS identifier WS initializer? WS SC
initializer      = EQUAL WS value_expr

var_decls        = var_decl*
var_decl         = WS ( def_decl / arg_decl )

format_decl      = FORMAT WS identifier WS LCB var_decls WS is_format_field WS annot_expr?  WS RCB
struct_decl      = STRUCT WS identifier WS LCB var_decls WS is_record_field WS annot_block? WS RCB
prompt_decl      = PROMPT WS identifier WS LCB
                       var_decls WS
                       is_record_field WS
                       channel_block__ WS
                       flow_block__ WS
                       return_stmt__ WS
                       annot_block__ WS
                   RCB

channel_block__  = channel_block?
flow_block__     = flow_block?
return_stmt__    = return_stmt?
annot_block__    = annot_block?


channel_block    = CHANNEL WS LCB WS ( channel_stmt WS )+ RCB
channel_stmt     = TO WS local_path_expr WS ( from_stmt / call_block )
from_stmt        = FROM WS path_expr WS SC
call_block       = CALL WS LCB WS
                       ( extern_stmt WS )?
                       ( entry_stmt WS )?
                       ( kwarg_stmt WS )*
                       ( bind_stmt  WS )*
                   RCB

extern_stmt      = EXTERN WS identifier WS SC
entry_stmt       = ENTRY  WS identifier WS SC
kwarg_stmt       = KWARG  WS identifier WS ( kwarg_from_stmt / kwarg_map_stmt ) WS SC
kwarg_from_stmt  = FROM WS path_expr
kwarg_map_stmt   = MAP  WS path_expr
bind_stmt        = BIND WS path_expr WS bind_as_stmt WS SC
bind_as_stmt     = AS WS path_expr

flow_block       = FLOW WS LCB WS ( flow_stmt WS )+ RCB
flow_stmt        = TO WS identifier flow_limit? WS flow_as_stmt? SC
flow_limit       = LSB WS int_literal WS RSB
flow_as_stmt     = AS WS string_literal

return_stmt      = RETURN WS ( return_block / return_expr )
return_block     = LCB WS return_as_stmt__? return_from_stmt__+ RCB
return_as_stmt__ = return_as_stmt WS
return_as_stmt   = AS WS string_literal WS SC
return_from_stmt__ = return_from_stmt WS
return_from_stmt = FROM WS path_expr WS SC
return_expr      = path_expr WS SC

annot_block      = ANNOTATE WS LCB WS annot_stmt__+ RCB
annot_stmt__     = annot_stmt WS
annot_stmt       = path_expr WS AS WS string_expr SC
annot_expr       = ANNOTATE WS string_expr SC

field_decls      = field_decl__*
field_decl__     = WS field_decl
field_decl       = field_name WS field_defn WS
field_name       = identifier array_slice?
field_defn       = is_format_field / is_record_field / field_detail
field_detail     = LCB WS ( is_format_field / is_record_field ) ( WS ( annot_expr / annot_block ) )? WS RCB
is_format_field  = IS WS (repeat_def / select_def / enum_def / regex_string / type_ref) WS SC
is_record_field  = IS WS LCB field_decls WS RCB

array_slice      = LSB WS int_literal ( WS COLON WS int_literal )? WS RSB

repeat_def       = REPEAT WS LPAR path_expr RPAR
select_def       = SELECT WS LPAR path_expr RPAR
enum_def         = ENUM   WS LPAR string_expr_list RPAR

type_ref         = identifier WS type_ref_param?
type_ref_param   = LT WS param_list WS GT

param_list       = param_expr param_list_cont*
param_list_cont  = WS COMMA WS param_list
param_expr       = param_expr_kw? value_expr
param_expr_kw    = identifier WS EQUAL  WS

path_expr        = global_path_expr / local_path_expr / input_path_expr
global_path_expr = identifier PERIOD sub_path_expr
local_path_expr  = PERIOD sub_path_expr
input_path_expr  = QMARK  sub_path_expr
sub_path_expr    = path_step sub_path_expr__?
sub_path_expr__  = PERIOD sub_path_expr
path_step        = identifier array_slice?

value_expr       = string_literal / int_literal__ / refexpr

string_expr_list = string_expr ( WS COMMA WS string_expr )*
string_expr      = string_literal / identifier
string_literal   = val_string / fmt_string

refexpr          = "@" identifier

# REGEX Nodes

identifier       = ~"[a-zA-Z_][a-zA-Z0-9_]*"

val_string       = '"' ~r'[^"]*' '"'
fmt_string       = 'f"' ~r'[^"]*' '"'
regex_string     = 'r"' ~r'[^"]*' '"'
int_literal__    = int_literal / int_infinty
int_literal     = ~r'\d+'
int_infinty      = "INF"

WS = ~"\s*"

# Keywords

AS       = "as"
IS       = "is"
TO       = "to"
MAP      = "map"
FROM     = "from"
CALL     = "call"
BIND     = "bind"
FLOW     = "flow"
ENUM     = "enum"
ENTRY    = "entry"
KWARG    = "kwarg"
DEFINE   = "define"
FORMAT   = "format"
STRUCT   = "struct"
PROMPT   = "prompt"
EXTERN   = "extern"
RETURN   = "return"
REPEAT   = "repeat"
SELECT   = "select"
CHANNEL  = "channel"
ARGUMENT = "argument"
ANNOTATE = "annotate"

# Punctuations

LT     = "<"
GT     = ">"
LPAR   = "("
RPAR   = ")"
LCB    = "{"
RCB    = "}"
LSB    = "["
RSB    = "]"
EQUAL  = "="
QMARK  = "?"
PERIOD = "."
COMMA  = ","
COLON  = ":"
SC     = ";"
""")
