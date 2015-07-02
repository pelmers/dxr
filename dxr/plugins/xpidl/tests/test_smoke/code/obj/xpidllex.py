# xpidllex.py. This file automatically created by PLY (version 3.6). Don't edit!
_tabversion   = '3.5'
_lextokens    = set(['TYPEDEF', 'INCLUDE', 'RSHIFT', 'LSHIFT', 'ATTRIBUTE', 'NATIVEID', 'NUMBER', 'NATIVE', 'IID', 'READONLY', 'RAISES', 'CDATA', 'IN', 'INTERFACE', 'CONST', 'IDENTIFIER', 'OUT', 'INOUT', 'HEXNUM'])
_lexreflags   = 0
_lexliterals  = '"(){}[],;:=|+-*'
_lexstateinfo = {'nativeid': 'exclusive', 'INITIAL': 'inclusive'}
_lexstatere   = {'nativeid': [('(?P<t_nativeid_NATIVEID>[^()\\n]+(?=\\)))', [None, ('t_nativeid_NATIVEID', 'NATIVEID')])], 'INITIAL': [('(?P<t_multilinecomment>/\\*(?s).*?\\*/)|(?P<t_singlelinecomment>(?m)//.*?$)|(?P<t_IID>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})|(?P<t_IDENTIFIER>(unsigned\\ long\\ long|unsigned\\ short|unsigned\\ long|long\\ long)(?!_?[A-Za-z][A-Za-z_0-9])|_?[A-Za-z][A-Za-z_0-9]*)|(?P<t_LCDATA>(?s)%\\{[ ]*C\\+\\+[ ]*\\n(?P<cdata>.*?\\n?)%\\}[ ]*(C\\+\\+)?)|(?P<t_INCLUDE>\\#include[ \\t]+"[^"\\n]+")|(?P<t_directive>\\#(?P<directive>[a-zA-Z]+)[^\\n]+)|(?P<t_newline>\\n+)|(?P<t_HEXNUM>0x[a-fA-F0-9]+)|(?P<t_NUMBER>-?\\d+)|(?P<t_LSHIFT><<)|(?P<t_RSHIFT>>>)', [None, ('t_multilinecomment', 'multilinecomment'), ('t_singlelinecomment', 'singlelinecomment'), ('t_IID', 'IID'), ('t_IDENTIFIER', 'IDENTIFIER'), None, ('t_LCDATA', 'LCDATA'), None, None, ('t_INCLUDE', 'INCLUDE'), ('t_directive', 'directive'), None, ('t_newline', 'newline'), (None, 'HEXNUM'), (None, 'NUMBER'), (None, 'LSHIFT'), (None, 'RSHIFT')])]}
_lexstateignore = {'nativeid': '', 'INITIAL': ' \t'}
_lexstateerrorf = {'nativeid': 't_ANY_error', 'INITIAL': 't_ANY_error'}
_lexstateeoff = {}
