import tempfile
from io import StringIO
from contextlib import redirect_stdout

from pyverilog.vparser.parser import parse


def parse_verilog_string(v_str: str) -> str:
    """
    Parse a Verilog string and return its AST as a string.
    """
    if not v_str.strip():
        return ""

    with tempfile.TemporaryDirectory() as tempdir:
        with tempfile.NamedTemporaryFile("w", suffix=".v") as f:
            f.write(v_str)
            f.flush()
            ast, _directives = parse([f.name], debug=False, outputdir=tempdir)
            buf = StringIO()
            ast.show(buf=buf)
            return buf.getvalue()


def parse_verilog_file(file_path: str) -> str:
    """
    Parse a Verilog file and return its AST as a string.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        ast, _directives = parse([file_path], debug=False, outputdir=tempdir)
        buf = StringIO()
        ast.show(buf=buf)
        return buf.getvalue()
