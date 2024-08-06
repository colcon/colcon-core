# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from io import StringIO
import os

from colcon_core.logging import colcon_logger

# The complicated import below is meant to handle 3 things:
# 1.  Empy 4 - the newest version as of this writing, which has a different API from Empy 3
# 2.  Empy 3 - the version available since 2003
# 3.  The ancient "em" tool, which has no relation to what we are doing here but sadly
#     shares the "em" package name with empy.  This isn't supported, but we detect it.

try:
    # Both Empy 4 and Empy 3 have the Interpreter object, while the ancient "em" does not.
    from em import Interpreter
except ImportError as e:
    try:
        import em  # noqa: F401
    except ImportError:
        e.msg += " The Python package 'empy' must be installed"
        raise e from None
    e.msg += " The Python package 'empy' must be installed and 'em' must " \
        'not be installed since both packages share the same namespace'
    raise e from None

try:
    # Only Empy 4 has the Configuration object
    from em import Configuration
    em_has_configuration = True
except ImportError as e:
    # We have Empy 3
    from em import OVERRIDE_OPT
    em_has_configuration = False

logger = colcon_logger.getChild(__name__)


def expand_template(template_path, destination_path, data):
    """
    Expand an EmPy template.

    The directory of the destination path is created if necessary.

    :param template_path: The patch of the template file
    :param destination_path: The path of the generated expanded file
    :param dict data: The data used for expanding the template
    :raises: Any exception which `em.Interpreter.string` might raise
    """
    output = StringIO()
    interpreter = None
    try:
        if em_has_configuration:
            config = Configuration(
                defaultRoot=str(template_path),
                defaultStdout=output,
                useProxy=False)
            interpreter = CachingInterpreter(config=config, dispatcher=False)
        else:
            # disable OVERRIDE_OPT to avoid saving / restoring stdout
            interpreter = CachingInterpreter(
                output=output, options={OVERRIDE_OPT: False})
        with template_path.open('r') as h:
            content = h.read()
        if em_has_configuration:
            interpreter.string(content, locals=data)
        else:
            interpreter.string(content, str(template_path), locals=data)

        output = output.getvalue()
    except Exception as e:  # noqa: F841
        logger.error(
            f"{e.__class__.__name__} processing template '{template_path}'")
        raise
    else:
        os.makedirs(str(destination_path.parent), exist_ok=True)
        # if the destination_path is a symlink remove the symlink
        # to avoid writing to the symlink destination
        if destination_path.is_symlink():
            destination_path.unlink()
        with destination_path.open('w') as h:
            h.write(output)
    finally:
        if interpreter is not None:
            interpreter.shutdown()


cached_tokens = {}

empy_inheritance = None
if em_has_configuration:
    empy_inheritance = Interpreter
else:
    class BypassStdoutInterpreter(Interpreter):
        """Interpreter for EmPy which keeps `stdout` unchanged."""

        def installProxy(self):  # noqa: D102 N802
            # avoid replacing stdout with ProxyFile
            pass

    empy_inheritance = BypassStdoutInterpreter

class CachingInterpreter(empy_inheritance):
    """Interpreter for EmPy which which caches parsed tokens."""

    def parse(self, scanner, locals=None):  # noqa: A002 D102
        global cached_tokens
        data = scanner.buffer
        # try to use cached tokens
        tokens = cached_tokens.get(data)
        if tokens is None:
            # collect tokens and cache them
            tokens = []
            while True:
                token = scanner.one()
                if token is None:
                    break
                tokens.append(token)
            cached_tokens[data] = tokens

        # reimplement the parse method using the (cached) tokens
        self.invoke('atParse', scanner=scanner, locals=locals)
        for token in tokens:
            self.invoke('atToken', token=token)
            if em_has_configuration:
                self.run(token, locals)
                scanner.accumulate()
            else:
                token.run(self, locals)
        if em_has_configuration:
            return True
