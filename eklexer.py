import ply.lex as lex
import sys

names ={}

# Keywords
RESERVED = {
  'if' : 'IF',
  'return' : 'RETURN',
  'while' : 'WHILE',
  'else' : 'ELSE',
  'print' : 'PRINT',
  'def' : 'DEF',
  'int' : 'INT',
  'cint' : 'CINT',
  'float' : 'FLOAT',
  'bool': 'BOOL',
  'void' : 'VOID',
  'ref' : 'REF',
  'noalias' : 'NOALIAS',
  'extern' : 'EXTERN',
  'true': 'TRUE',
  'false': 'FALSE'
}

# List of token names.
tokens = [
   'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'ASSIGN',
   'EQUAL', 'LT', 'GT', 'OR', 'AND', 'NOT',
   'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE', 'LBRACKET', 'RBRACKET', 'COMMA',
   'LIT', 'SLIT', 'ID', 'VARID', 'SEMICOLON'
] + list(RESERVED.values())

# Regular expression rules for simple tokens
t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_ASSIGN = r'='

t_EQUAL= r'=='
t_LT = r'<'
t_GT = r'>'
t_AND = r'&&'
t_OR = r'\|\|'
t_NOT = r'!'

t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_LBRACE = r'{'
t_RBRACE = r'}'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_COMMA = r','

t_SEMICOLON = r';'
t_ignore  = ' \t'

# ID
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = RESERVED.get(t.value, "ID")
    return t

# VARID
def t_VARID(t):
  r'[$][\s]*[a-zA-Z_][a-zA-Z0-9_]*'
  t.value = t.value.strip()
  return t

# lit
def t_LIT(t):
  r'[0-9]+(\.[0-9]+)?'
  t.value = t.value.replace(" ", "")
  if '.' in t.value:
    t.value = float(t.value)
  else:
    t.value = int(t.value)
  t.type = 'LIT'
  return t

# slit
def t_SLIT(t):
  r'"[^"]*"'
  t.value = t.value[1:-1]
  return t

# Comment
def t_COMMENT(t):
  r'\#.*'
  pass

# Define a rule so we can track line numbers
def t_NEWLINE(t):
  r'\n+'
  t.lexer.lineno += len(t.value)
  pass

# Error
def t_error(t):
    print('error: Illegal character: ' + t.value[0])
    t.lexer.skip(1)

# Build the lexer
lexer = lex.lex()
