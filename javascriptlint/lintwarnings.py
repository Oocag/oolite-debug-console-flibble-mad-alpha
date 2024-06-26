# vim: ts=4 sw=4 expandtab
# cag: 30-6-22, added LET & CONST support
""" This module contains all the warnings. To add a new warning, define a
function. Its name should be in lowercase and words should be separated by
underscores.

The function should be decorated with a @lookfor call specifying the nodes it
wants to examine. The node names may be in the tok.KIND or (tok.KIND, op.OPCODE)
format. To report a warning, the function should raise a LintWarning exception.

For example:

    @lookfor(tok.NODEKIND, (tok.NODEKIND, op.OPCODE))
    def warning_name(node):
        if questionable:
            raise LintWarning(node)
"""
import itertools
import re

from jsengine import js_util
from jsengine.parser import kind as tok
from jsengine.parser import op
from . import util

_ALL_TOKENS = list(tok.__dict__.values())

def _get_assigned_lambda(node):
    """ Given a node "x = function() {}", returns "function() {}".
    """
    value = None
    if node.kind == tok.SEMI:
        assign_node, = node.kids
        if assign_node and assign_node.kind == tok.ASSIGN:
            ignored, value = assign_node.kids
    elif node.kind in [tok.VAR, tok.LET, tok.CONST]:
        variables = node.kids
        if variables:
            value, = variables[-1].kids

    if value and value.kind == tok.FUNCTION and value.opcode == op.ANONFUNOBJ:
        return value

    return None

# TODO: document inspect, node:opcode, etc

warnings = {
    'comparison_type_conv': 'comparisons against null, 0, true, false, or an empty string allowing implicit type conversion (use === or !==)',
    'default_not_at_end': 'the default case is not at the end of the switch statement',
    'duplicate_case_in_switch': 'duplicate case in switch statement',
    'missing_default_case': 'missing default case in switch statement',
    'with_statement': 'with statement hides undeclared variables; use temporary variable instead',
    'useless_comparison': 'useless comparison; comparing identical expressions',
    'use_of_label': 'use of label',
    'misplaced_regex': 'regular expressions should be preceded by a left parenthesis, assignment, colon, or comma',
    'assign_to_function_call': 'assignment to a function call',
    'equal_as_assign': 'test for equality (==) mistyped as assignment (=)?',
    'ambiguous_else_stmt': 'the else statement could be matched with one of multiple if statements (use curly braces to indicate intent',
    'block_without_braces': 'block statement without curly braces',
    'ambiguous_nested_stmt': 'block statements containing block statements should use curly braces to resolve ambiguity',
    'inc_dec_within_stmt': 'increment (++) and decrement (--) operators used as part of greater statement',
    'comma_separated_stmts': 'multiple statements separated by commas (use semicolons?)',
    'empty_statement': 'empty statement or extra semicolon',
    'missing_break': 'missing break statement',
    'missing_break_for_last_case': 'missing break statement for last case in switch',
    'multiple_plus_minus': 'unknown order of operations for successive plus (e.g. x+++y) or minus (e.g. x---y) signs',
    'useless_assign': 'useless assignment',
    'unreachable_code': 'unreachable code',
    'meaningless_block': 'meaningless block; curly braces have no impact',
    'useless_void': 'use of the void type may be unnecessary (void is always undefined)',
    'parseint_missing_radix': 'parseInt missing radix parameter',
    'leading_decimal_point': 'leading decimal point may indicate a number or an object member',
    'trailing_decimal_point': 'trailing decimal point may indicate a number or an object member',
    'octal_number': 'leading zeros make an octal number',
    'trailing_comma': 'extra comma is not recommended in object initializers',
    'trailing_comma_in_array': 'extra comma is not recommended in array initializers',
    'useless_quotes': 'the quotation marks are unnecessary',
    'mismatch_ctrl_comments': 'mismatched control comment; "ignore" and "end" control comments must have a one-to-one correspondence',
    'redeclared_var': 'redeclaration of {name}',
    'undeclared_identifier': 'undeclared identifier: {name}',
    'unreferenced_argument': 'argument declared but never referenced: {name}',
    'unreferenced_function': 'function is declared but never referenced: {name}',
    'unreferenced_variable': 'variable is declared but never referenced: {name}',
    'jsl_cc_not_understood': 'couldn\'t understand control comment using /*jsl:keyword*/ syntax',
    'nested_comment': 'nested comment',
    'legacy_cc_not_understood': 'couldn\'t understand control comment using /*@keyword@*/ syntax',
    'var_hides_arg': 'variable {name} hides argument',
    'identifier_hides_another': 'identifer {name} hides an identifier in a parent scope',
    'duplicate_formal': 'duplicate formal argument {name}',
    'missing_semicolon': 'missing semicolon',
    'missing_semicolon_for_lambda': 'missing semicolon for lambda assignment',
    'ambiguous_newline': 'unexpected end of line; it is ambiguous whether these lines are part of the same statement',
    'missing_option_explicit': 'the "option explicit" control comment is missing',
    'partial_option_explicit': 'the "option explicit" control comment, if used, must be in the first script tag',
    'dup_option_explicit': 'duplicate "option explicit" control comment',
    'invalid_fallthru': 'unexpected "fallthru" control comment',
    'invalid_pass': 'unexpected "pass" control comment',
    'want_assign_or_call': 'expected an assignment or function call',
    'no_return_value': 'function {name} does not always return a value',
    'anon_no_return_value': 'anonymous function does not always return value',
    'unsupported_version': 'JavaScript {version} is not supported',
    'incorrect_version': 'Expected /*jsl:content-type*/ control comment. The script was parsed with the wrong version.',
    'for_in_missing_identifier': 'for..in should have identifier on left side',
    'misplaced_function': 'unconventional use of function expression',
    'function_name_missing': 'anonymous function should be named to match property name {name}',
    'function_name_mismatch': 'function name {fn_name} does not match property name {prop_name}',
    'trailing_whitespace': 'trailing whitespace',
    'e4x_deprecated': 'e4x is deprecated',
    'ambiguous_numeric_prop': 'numeric property should be normalized; use {normalized}',
    'duplicate_property': 'duplicate property in object initializer',
    'unexpected_not_in': 'the ! operator is unexpected; add clarifying parentheses',
    'unexpected_not_comparison': 'the ! operator is unexpected; add clarifying parentheses or rewrite the comparison',
}

errors = {
    'semi_before_stmnt': 'missing semicolon before statement',
    'syntax_error': 'syntax error',
    'expected_tok': 'expected token: {token}',
    'unexpected_char': 'unexpected character: {char}',
    'unexpected_eof': 'unexpected end of file',
    'io_error': '{error}',
}

def format_error(errname, **errargs):
    errdesc = errors.get(errname, warnings.get(errname))
    assert errdesc is not None, errname

    try:
        keyword = re.compile(r"{(\w+)}")
        errdesc = keyword.sub(lambda match: errargs[match.group(1)], errdesc)
    except (TypeError, KeyError) as error:
        raise KeyError('Invalid keyword in error {}: {}'.format(errname, errdesc)) from error
    return errdesc

_visitors = []
def lookfor(*args):
    def decorate(fn):
        fn.warning = fn.__name__.rstrip('_')
        assert fn.warning in warnings, 'Missing warning description: %s' % fn.warning

        for arg in args:
            _visitors.append((arg, fn))
    return decorate

_visitor_classes = []
def lookfor_class(*args):
    def decorate(cls):
        # Convert the class name to camel case
        camelcase = re.sub('([A-Z])', r'_\1', cls.__name__).lower().lstrip('_')

        cls.warning = camelcase.rstrip('_')
        assert cls.warning in warnings, \
                'Missing warning description: %s' % cls.warning

        for arg in args:
            _visitor_classes.append((arg, cls))
    return decorate

class LintWarning(Exception):
    def __init__(self, node, **errargs):
        self.node = node
        self.errargs = errargs

def _get_branch_in_for(node):
        " Returns None if this is not one of the branches in a 'for' "
        if node.parent and node.parent.kind == tok.RESERVED and \
            node.parent.parent.kind == tok.FOR:
            return node.node_index
        return None

def _get_exit_points(node):
    """ Returns a set of exit points, which may be:
        * None, indicating a code path with no specific exit point.
        * a node of type tok.BREAK, tok.RETURN, tok.THROW.
    """
    if node.kind == tok.LC:
        exit_points = {None}
        for kid in node.kids:
            if kid:
                # Merge in the kid's exit points.
                kid_exit_points = _get_exit_points(kid)
                exit_points |= kid_exit_points

                # Stop if the kid always exits.
                if not None in kid_exit_points:
                    exit_points.discard(None)
                    break
    elif node.kind == tok.IF:
        # Only if both branches have an exit point
        cond_, if_, else_ = node.kids
        exit_points = _get_exit_points(if_)
        if else_:
            exit_points |= _get_exit_points(else_)
        else:
            exit_points.add(None)
    elif node.kind == tok.SWITCH:
        exit_points = {None}

        switch_has_default = False
        switch_has_final_fallthru = True

        switch_var, switch_stmts = node.kids
        for iter_node in switch_stmts.kids:
            case_val, case_stmt = iter_node.kids
            case_exit_points = _get_exit_points(case_stmt)
            switch_has_default = switch_has_default or iter_node.kind == tok.DEFAULT
            switch_has_final_fallthru = None in case_exit_points
            exit_points |= case_exit_points

        # Correct the "None" exit point.
        exit_points.remove(None)

        # Convert "break" into None
        def break_to_none(node):
            if node and node.kind != tok.BREAK:
                return node
            return None
        exit_points = set(map(break_to_none, exit_points))

        # Check if the switch had a default case
        if not switch_has_default:
            exit_points.add(None)

        # Check if the final case statement had a fallthru
        if switch_has_final_fallthru:
            exit_points.add(None)
    elif node.kind == tok.BREAK:
        exit_points = {node}
    elif node.kind == tok.CONTINUE:
        exit_points = {node}
    elif node.kind == tok.WITH:
        exit_points = _get_exit_points(node.kids[-1])
    elif node.kind == tok.RETURN:
        exit_points = {node}
    elif node.kind == tok.THROW:
        exit_points = {node}
    elif node.kind == tok.TRY:
        try_, catch_, finally_ = node.kids

        exit_points = _get_exit_points(try_)

        if catch_:
            assert catch_.kind == tok.RESERVED
            catch_, = catch_.kids
            assert catch_.kind == tok.LEXICALSCOPE
            catch_, = catch_.kids
            assert catch_.kind == tok.CATCH
            assert len(catch_.kids) == 3
            catch_ = catch_.kids[-1]
            assert catch_.kind == tok.LC

            exit_points |= _get_exit_points(catch_)

        if finally_:
            finally_exit_points = _get_exit_points(finally_)
            if None in finally_exit_points:
                # The finally statement does not add a missing exit point.
                finally_exit_points.remove(None)
            else:
                # If the finally statement always returns, the other
                # exit points are irrelevant.
                if None in exit_points:
                    exit_points.remove(None)

            exit_points |= finally_exit_points

    else:
        exit_points = {None}

    return exit_points

def _loop_has_unreachable_condition(node):
    for exit_point in _get_exit_points(node):
        if exit_point is None:
            return False
        if exit_point.kind == tok.CONTINUE:
            return False
    return True

@lookfor((tok.EQOP, op.EQ))
def comparison_type_conv(node):
    for kid in node.kids:
        if kid.kind == tok.PRIMARY and kid.opcode in (op.NULL, op.TRUE, op.FALSE):
            raise LintWarning(kid)
        if kid.kind == tok.NUMBER and not kid.dval:
            raise LintWarning(kid)
        if kid.kind == tok.STRING and not kid.atom:
            raise LintWarning(kid)

@lookfor(tok.DEFAULT)
def default_not_at_end(node):
    siblings = node.parent.kids
    if node.node_index != len(siblings)-1:
        raise LintWarning(siblings[node.node_index+1])

@lookfor(tok.CASE)
def duplicate_case_in_switch(node):
    # Only look at previous siblings
    siblings = node.parent.kids
    siblings = siblings[:node.node_index]
    # Compare values (first kid)
    node_value = node.kids[0]
    for sibling in siblings:
        if sibling.kind == tok.CASE:
            sibling_value = sibling.kids[0]
            if node_value.is_equivalent(sibling_value, True):
                raise LintWarning(node)

@lookfor(tok.SWITCH)
def missing_default_case(node):
    value, cases = node.kids
    for case in cases.kids:
        if case.kind == tok.DEFAULT:
            return
    raise LintWarning(node)

@lookfor(tok.WITH)
def with_statement(node):
    raise LintWarning(node)

@lookfor(tok.EQOP, tok.RELOP)
def useless_comparison(node):
    for lvalue, rvalue in itertools.combinations(node.kids, 2):
        if lvalue.is_equivalent(rvalue):
            raise LintWarning(node)

@lookfor((tok.COLON, op.NAME))
def use_of_label(node):
    raise LintWarning(node)

@lookfor((tok.OBJECT, op.REGEXP))
def misplaced_regex(node):
    if node.parent.kind == tok.NAME and node.parent.opcode == op.SETNAME:
        return # Allow in var statements
    if node.parent.kind == tok.ASSIGN and node.parent.opcode == op.NOP:
        return # Allow in assigns
    if node.parent.kind == tok.COLON and node.parent.parent.kind == tok.RC:
        return # Allow in object literals
    if node.parent.kind == tok.LP and node.parent.opcode == op.CALL:
        return # Allow in parameters
    if node.parent.kind == tok.DOT and node.parent.opcode == op.GETPROP:
        return # Allow in /re/.property
    if node.parent.kind == tok.RETURN:
        return # Allow for return values
    raise LintWarning(node)

@lookfor(tok.ASSIGN)
def assign_to_function_call(node):
    kid = node.kids[0]
    # Unpack parens.
    while kid.kind == tok.RP:
       kid, = kid.kids
    if kid.kind == tok.LP:
        raise LintWarning(node)

@lookfor((tok.ASSIGN, None))
def equal_as_assign(node):
    # Allow in VAR, LET & CONST statements.
    if node.parent.parent \
			and node.parent.parent.kind in [tok.VAR, tok.LET, tok.CONST]:
        return

    if not node.parent.kind in (tok.SEMI, tok.RESERVED, tok.RP, tok.COMMA,
                                tok.ASSIGN):
        raise LintWarning(node)

@lookfor(tok.IF)
def ambiguous_else_stmt(node):
    # Only examine this node if it has an else statement.
    condition, if_, else_ = node.kids
    if not else_:
        return

    tmp = node
    while tmp:
        # Curly braces always clarify if statements.
        if tmp.kind == tok.LC:
            return
        # Else is only ambiguous in the first branch of an if statement.
        if tmp.parent.kind == tok.IF and tmp.node_index == 1:
            raise LintWarning(else_)
        tmp = tmp.parent

@lookfor(tok.IF, tok.WHILE, tok.DO, tok.FOR, tok.WITH)
def block_without_braces(node):
    if node.kids[1].kind != tok.LC:
        raise LintWarning(node.kids[1])

_block_nodes = (tok.IF, tok.WHILE, tok.DO, tok.FOR, tok.WITH)
@lookfor(*_block_nodes)
def ambiguous_nested_stmt(node):
    # Ignore "else if"
    if node.kind == tok.IF and node.node_index == 2 and node.parent.kind == tok.IF:
        return

    # If the parent is a block, it means a block statement
    # was inside a block statement without clarifying curlies.
    # (Otherwise, the node type would be tok.LC.)
    if node.parent.kind in _block_nodes:
        raise LintWarning(node)

@lookfor(tok.INC, tok.DEC)
def inc_dec_within_stmt(node):
    if node.parent.kind == tok.SEMI:
        return

    # Allow within the third part of the "for"
    tmp = node
    while tmp and tmp.parent and tmp.parent.kind == tok.COMMA:
        tmp = tmp.parent
    if tmp and tmp.node_index == 2 and \
        tmp.parent.kind == tok.RESERVED and \
        tmp.parent.parent.kind == tok.FOR:
        return

    raise LintWarning(node)

@lookfor(tok.COMMA)
def comma_separated_stmts(node):
    # Allow within the first and third part of "for(;;)"
    if _get_branch_in_for(node) in (0, 2):
        return
    # This is an array
    if node.parent.kind == tok.RB:
        return
    raise LintWarning(node)

@lookfor(tok.SEMI)
def empty_statement(node):
    if not node.kids[0]:
        raise LintWarning(node)
@lookfor(tok.LC)
def empty_statement_(node):
    if node.kids:
        return
    # Ignore the outermost block.
    if not node.parent:
        return
    # Some empty blocks are meaningful.
    if node.parent.kind in (tok.CATCH, tok.CASE, tok.DEFAULT, tok.SWITCH, tok.FUNCTION):
        return
    raise LintWarning(node)

@lookfor(tok.CASE, tok.DEFAULT)
def missing_break(node):
    # The last item is handled separately
    if node.node_index == len(node.parent.kids)-1:
        return
    case_contents = node.kids[1]
    assert case_contents.kind == tok.LC
    # Ignore empty case statements
    if not case_contents.kids:
        return
    if None in _get_exit_points(case_contents):
        # Show the warning on the *next* node.
        raise LintWarning(node.parent.kids[node.node_index+1])

@lookfor(tok.CASE, tok.DEFAULT)
def missing_break_for_last_case(node):
    if node.node_index < len(node.parent.kids)-1:
        return
    case_contents = node.kids[1]
    assert case_contents.kind == tok.LC
    if None in _get_exit_points(case_contents):
        raise LintWarning(node)

@lookfor(tok.INC)
def multiple_plus_minus(node):
    if node.node_index == 0 and node.parent.kind == tok.PLUS:
        raise LintWarning(node)
@lookfor(tok.DEC)
def multiple_plus_minus_(node):
    if node.node_index == 0 and node.parent.kind == tok.MINUS:
        raise LintWarning(node)

@lookfor((tok.NAME, op.SETNAME))
def useless_assign(node):
    if node.parent.kind == tok.ASSIGN and node.parent.opcode not in (op.MUL, op.ADD, op.LSH,
                                                                     op.RSH, op.URSH):
        assert node.node_index == 0
        value = node.parent.kids[1]
    elif node.parent.kind in [tok.VAR, tok.LET, tok.CONST]:
        value = node.kids[0]
    else:
        value = None
    if value and value.kind == tok.NAME and node.atom == value.atom:
        raise LintWarning(node)

@lookfor(tok.BREAK, tok.CONTINUE, tok.RETURN, tok.THROW)
def unreachable_code(node):
    if node.parent.kind == tok.LC:
        for sibling in node.parent.kids[node.node_index+1:]:
            if sibling.kind in [tok.VAR, tok.LET, tok.CONST]:
                # Look for a variable assignment
                for variable in sibling.kids:
                    value, = variable.kids
                    if value:
                        raise LintWarning(value)
            elif sibling.kind == tok.FUNCTION:
                # Functions are always declared.
                pass
            else:
                raise LintWarning(sibling)

@lookfor(tok.FOR)
def unreachable_code_(node):
    # Warn if the for loop always exits.
    preamble, code = node.kids
    if preamble.kind == tok.RESERVED:
        pre, condition, post = preamble.kids
        if post:
            if _loop_has_unreachable_condition(code):
                raise LintWarning(post)

@lookfor(tok.DO)
def unreachable_code__(node):
    # Warn if the do..while loop always exits.
    code, condition = node.kids
    if _loop_has_unreachable_condition(code):
        raise LintWarning(condition)

#TODO: @lookfor(tok.IF)
def meaningless_block(node):
    condition, if_, else_ = node.kids
    if condition.kind == tok.PRIMARY and condition.opcode in (op.TRUE, op.FALSE, op.NULL):
        raise LintWarning(condition)
#TODO: @lookfor(tok.WHILE)
def meaningless_blocK_(node):
    condition = node.kids[0]
    if condition.kind == tok.PRIMARY and condition.opcode in (op.FALSE, op.NULL):
        raise LintWarning(condition)
@lookfor(tok.LC)
def meaningless_block__(node):
    if node.parent and node.parent.kind == tok.LC:
        raise LintWarning(node)

@lookfor((tok.UNARYOP, op.VOID))
def useless_void(node):
    raise LintWarning(node)

@lookfor((tok.LP, op.CALL))
def parseint_missing_radix(node):
    if node.kids[0].kind == tok.NAME and node.kids[0].atom == 'parseInt' and len(node.kids) <= 2:
        raise LintWarning(node)

@lookfor(tok.NUMBER)
def leading_decimal_point(node):
    if node.atom.startswith('.'):
        raise LintWarning(node)

@lookfor(tok.NUMBER)
def trailing_decimal_point(node):
    if node.parent.kind == tok.DOT:
        raise LintWarning(node)
    if node.atom.endswith('.'):
        raise LintWarning(node)

_octal_regexp = re.compile('^0[0-9]')
@lookfor(tok.NUMBER)
def octal_number(node):
    if _octal_regexp.match(node.atom):
        raise LintWarning(node)

@lookfor(tok.RC)
def trailing_comma(node):
    if node.end_comma:
        # Warn on the last value in the dictionary.
        last_item = node.kids[-1]
        assert last_item.kind == tok.COLON
        key, value = last_item.kids
        raise LintWarning(value)

@lookfor(tok.RB)
def trailing_comma_in_array(node):
    if node.end_comma:
        # Warn on the last value in the array.
        raise LintWarning(node.kids[-1])

@lookfor(tok.STRING)
def useless_quotes(node):
    if node.node_index == 0 and node.parent.kind == tok.COLON:
        # Only warn if the quotes could safely be removed.
        if util.isidentifier(node.atom):
            raise LintWarning(node)

@lookfor(tok.SEMI)
def want_assign_or_call(node):
    child, = node.kids
    # Ignore empty statements.
    if not child:
        return
    # NOTE: Don't handle comma-separated statements.
    if child.kind in (tok.ASSIGN, tok.INC, tok.DEC, tok.DELETE, tok.COMMA):
        return
    if child.kind == tok.YIELD:
        return
    # Ignore function calls.
    if child.kind == tok.LP and child.opcode == op.CALL:
        return
    # Allow new function() { } as statements.
    if child.kind == tok.NEW:
        # The first kid is the constructor, followed by its arguments.
        grandchild = child.kids[0]
        if grandchild.kind == tok.FUNCTION:
            return
    raise LintWarning(child)

def _check_return_value(node):
    name = node.fn_name or '(anonymous function)'

    def is_return_with_val(node):
        return node and node.kind == tok.RETURN and node.kids[0]
    def is_return_without_val(node):
        return node and node.kind == tok.RETURN and not node.kids[0]

    node, = node.kids
    assert node.kind == tok.LC

    exit_points = _get_exit_points(node)
    if list(filter(is_return_with_val, exit_points)):
        # If the function returns a value, find all returns without a value.
        returns = list(filter(is_return_without_val, exit_points))
        returns.sort(key=lambda node: node.start_offset)
        if returns:
            raise LintWarning(returns[0], name=name)
        # Warn if the function sometimes exits naturally.
        if None in exit_points:
            raise LintWarning(node, name=name)

@lookfor(tok.FUNCTION)
def no_return_value(node):
    if node.fn_name:
        _check_return_value(node)

@lookfor(tok.FUNCTION)
def anon_no_return_value(node):
    if not node.fn_name:
        _check_return_value(node)

@lookfor((tok.FOR, op.FORIN))
def for_in_missing_identifier(node):
    assert node.kids[0].kind == tok.IN
    left, right = node.kids[0].kids
    if not left.kind in (tok.VAR, tok.LET, tok.NAME):
        raise LintWarning(left)

@lookfor(tok.NUMBER)
def ambiguous_numeric_prop(node):
    normalized = js_util.numeric_property_str(node)
    if (node.node_index == 0 and node.parent.kind == tok.COLON) or \
            (node.node_index == 1 and node.parent.kind == tok.LB):
        if normalized != node.atom:
            raise LintWarning(node, normalized=normalized)

@lookfor(tok.COLON)
def duplicate_property(node):
    if not node.parent.kind == tok.RC:
        return

    node_value = js_util.object_property_str(node)
    for sibling in node.parent.kids[:node.node_index]:
        sibling_value = js_util.object_property_str(sibling)
        if node_value == sibling_value:
            raise LintWarning(node)

@lookfor(tok.FUNCTION)
def misplaced_function(node):
    # Ignore function statements.
    if node.opcode in (None, op.CLOSURE):
        return

    # Ignore parens.
    parent = node.parent
    while parent.kind == tok.RP:
        parent = parent.parent

    # Allow x = x || ...
    if parent.kind == tok.OR and len(parent.kids) == 2 and \
            node is parent.kids[-1]:
        parent = parent.parent

    if parent.kind == tok.NAME and parent.opcode == op.SETNAME:
        return # Allow in var statements
    if parent.kind == tok.ASSIGN and parent.opcode == op.NOP:
        return # Allow in assigns
    if parent.kind == tok.COLON and parent.parent.kind == tok.RC:
        return # Allow in object literals
    if parent.kind == tok.LP and parent.opcode in (op.CALL, op.SETCALL):
        return # Allow in parameters
    if parent.kind == tok.RETURN:
        return # Allow for return values
    if parent.kind == tok.NEW:
        return # Allow as constructors
    raise LintWarning(node)

@lookfor((tok.UNARYOP, op.NOT))
def unexpected_not_in(node):
    # Avoid for(!s in o)
    if node.parent and node.parent.kind == tok.IN:
        raise LintWarning(node)

@lookfor((tok.UNARYOP, op.NOT))
def unexpected_not_comparison(node):
    # Avoid use in comparisons.
    if node.parent and node.parent.kind == tok.RELOP:
        raise LintWarning(node)

    if node.parent and node.parent.kind == tok.EQOP:
        # Allow !!
        kid, = node.kids
        if kid.kind == tok.UNARYOP and kid.opcode == op.NOT:
            return

        # Allow when compared against !
        for i, kid in enumerate(node.parent.kids):
            if i == node.node_index:
                continue
            if kid.kind != tok.UNARYOP or kid.opcode != op.NOT:
                break
        else:
            return

        raise LintWarning(node)

def _get_function_property_name(node):
    # Ignore function statements.
    if node.opcode in (None, op.CLOSURE):
        return None

    # Ignore parens.
    parent = node.parent
    while parent.kind == tok.RP:
        parent = parent.parent

    # Allow x = x || ...
    if parent.kind == tok.OR and len(parent.kids) == 2 and \
            node is parent.kids[-1]:
        parent = parent.parent

    # Var assignment.
    if parent.kind == tok.NAME and parent.opcode == op.SETNAME:
        return parent.atom

    # Assignment.
    if parent.kind == tok.ASSIGN and parent.opcode == op.NOP:
        if parent.kids[0].kind == tok.NAME and \
           parent.kids[0].opcode == op.SETNAME:
            return parent.kids[0].atom
        if parent.kids[0].kind == tok.DOT and \
           parent.kids[0].opcode == op.SETPROP:
            return parent.kids[0].atom
        return '<error>'

    # Object literal.
    if parent.kind == tok.COLON and parent.parent.kind == tok.RC:
        return parent.kids[0].atom

    return None

def _get_expected_function_name(node, decorate):
    name = _get_function_property_name(node)
    if name and decorate:
        return '__%s' % name
    return name

@lookfor_class(tok.FUNCTION)
class FunctionNameMissing:
    def __init__(self, conf):
        self._decorate = conf['decorate_function_name_warning']

    def __call__(self, node):
        if node.fn_name:
            return

        expected_name = _get_expected_function_name(node, self._decorate)
        if not expected_name is None:
            raise LintWarning(node, name=expected_name)

@lookfor_class(tok.FUNCTION)
class FunctionNameMismatch:
    def __init__(self, conf):
        self._decorate = conf['decorate_function_name_warning']

    def __call__(self, node):
        if not node.fn_name:
            return

        expected_name = _get_expected_function_name(node, self._decorate)
        if expected_name is None:
            return

        if expected_name != node.fn_name:
            raise LintWarning(node, fn_name=node.fn_name,
                              prop_name=expected_name)

@lookfor()
def mismatch_ctrl_comments(node):
    pass

@lookfor()
def redeclared_var(node):
    pass

@lookfor()
def undeclared_identifier(node):
    pass

@lookfor()
def jsl_cc_not_understood(node):
    pass

@lookfor()
def nested_comment(node):
    pass

@lookfor()
def legacy_cc_not_understood(node):
    pass

@lookfor()
def var_hides_arg(node):
    pass

@lookfor()
def duplicate_formal(node):
    pass

@lookfor(*_ALL_TOKENS)
def missing_semicolon(node):
    if node.no_semi:
        if not _get_assigned_lambda(node):
            raise LintWarning(node)

@lookfor(*_ALL_TOKENS)
def missing_semicolon_for_lambda(node):
    if node.no_semi:
        # spidermonkey sometimes returns incorrect positions for var
        # statements, so use the position of the lambda instead.
        lambda_ = _get_assigned_lambda(node)
        if lambda_:
            raise LintWarning(lambda_)

@lookfor()
def ambiguous_newline(node):
    pass

@lookfor()
def missing_option_explicit(node):
    pass

@lookfor()
def partial_option_explicit(node):
    pass

@lookfor()
def dup_option_explicit(node):
    pass

def make_visitors(conf):
    all_visitors = list(_visitors)
    for kind, klass in _visitor_classes:
        all_visitors.append((kind, klass(conf=conf)))

    visitors = {}
    for kind, func in all_visitors:
        try:
            visitors[kind].append(func)
        except KeyError:
            visitors[kind] = [func]
    return visitors

