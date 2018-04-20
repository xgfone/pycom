# -*- coding: utf-8 -*-

import sys

from argparse import ArgumentParser
from xutils import is_string


class Configuration(object):
    class Group(object):
        def __init__(self, group_name):
            self.__name = group_name

        def __repr__(self):
            attrs = []
            for key, value in vars(self).items():
                if key != "_Group__name":
                    attrs.append("{0}={1}".format(key, value))
            return "{0}({1})".format(self.__class__.__name__, ", ".join(attrs))

        def __contains__(self, name):
            return hasattr(self, name)

        def __getattr__(self, name):
            e = "The group '{0}' has no the option '{1}'"
            raise AttributeError(e.format(self.__name, name))

        def __setitem__(self, name, value):
            setattr(self, name, value)

        def __getitem__(self, name):
            try:
                return getattr(self, name)
            except AttributeError:
                e = "The group '{0}' has no the option '{1}'"
                raise KeyError(e.format(self.__name, name))

        def items(self):
            d = vars(self)
            d.pop("_Group__name")
            return d.items()

    __slots__ = ["_default_group_name", "_default_group", "_allow_empty",
                 "_encoding", "_parsed", "_caches", "_opts", "_bool_true",
                 "_bool_false", "_py2", "_description", "_version"]

    def __init__(self, description=None, allow_empty=False, encoding="utf-8",
                 default_group="DEFAULT", version=None):
        """A simple configuration file parser based on the format INI.

        When an configuration option does not exist, for getting one default
        value, not raising an exception, please use the method of get(), or the
        builtin function of getattr().
        """

        self._parsed = False
        self._description = description
        self._default_group_name = default_group
        self._default_group = Configuration.Group(self._default_group_name)
        self._allow_empty = allow_empty
        self._encoding = encoding
        self._version = version if version else "Unknown"

        self._caches = {self._default_group_name: self._default_group}
        self._opts = {}

        self._bool_true = ["t", "1", "on", "true"]
        self._bool_false = ["f", "0", "off", "false"]

        try:
            "".decode()
        except AttributeError:
            self._py2 = False
        else:
            self._py2 = True

    def __getattr__(self, name):
        if not self._parsed:
            raise Exception("Not parsed")

        try:
            return self._caches[name]
        except KeyError:
            pass

        msg = "'{0}' object has no attribute '{1}'"
        raise AttributeError(msg.format(self.__class__.__name__, name))

    def __getitem__(self, name):
        if not self._parsed:
            raise Exception("Not parsed")

        _name = self._uniformize(name)
        try:
            return self._caches[_name]
        except KeyError:
            pass

        msg = "'{0}' has no key '{1}'"
        raise KeyError(msg.format(self.__class__.__name__, name))

    def __repr__(self):
        attrs = []
        for key, value in self._caches.items():
            attrs.append("{0}={1}".format(key, value))
        return "{0}({1})".format(self.__class__.__name__, ", ".join(attrs))

    def _set_group_opt(self, group_name, opt_name, opt_value, force=False):
        gname = group_name if group_name else self._default_group_name
        group = self._caches[gname]
        if hasattr(group, opt_name) and not force:
            e = "The group '{0}' has had the option of '{1}'"
            raise ValueError(e.format(gname, opt_name))
        setattr(self._caches[gname], opt_name, opt_value)

    def _register(self, name, parser, default=None, group=None, help=None, short=None):
        if self._parsed:
            raise Exception("Have been parsed")

        name = self._uniformize(name)
        group = self._uniformize(group if group else self._default_group_name)
        self._opts.setdefault(group, {})

        if name in self._opts[group]:
            raise KeyError("The option {0} has been regisetered".format(name))

        self._opts[group][name] = (parser, default, help, short)
        self._caches.setdefault(group, Configuration.Group(group))

    def _parse_int(self, value):
        return int(value)

    def _parse_float(self, value):
        return float(value)

    def _parse_bool(self, value):
        if isinstance(value, bool):
            return value
        elif not is_string(value):
            return bool(value)

        value = value.lower()
        if value in self._bool_true:
            return True
        elif value in self._bool_false:
            return False
        raise ValueError("invalid bool value '{0}'".format(value))

    def _parse_string(self, value):
        if self._py2:
            if isinstance(value, str):
                return value.decode(self._encoding)
        else:
            if not isinstance(value, str):
                return value.decode(self._encoding)
        return value

    def _parse_ints(self, value):
        return self._parse_list(self._parse_int, value)

    def _parse_strings(self, value):
        return self._parse_list(self._parse_string, value)

    def _parse_list(self, parser, value):
        if isinstance(value, (list, tuple)):
            vs = value
        else:
            vs = (v.strip() for v in value.split(",") if v.strip())
        return tuple((parser(v) for v in vs))

    def _uniformize(self, name):
        return name.replace("-", "_")

    def _unniformize(self, name):
        return name.replace("_", "-")

    def parsed(self):
        """Return True if it has been parsed, or False."""
        return self._parsed

    def parse_files(self, filenames=""):
        """Parse the INI configuration files.

        The argument is either a string standing for the path of the
        configuration file, or a list of them.
        """
        if self._parsed:
            raise Exception("Have been parsed")
        self._parsed = True

        if filenames:
            if not isinstance(filenames, (list, tuple)):
                filenames = self._parse_string(filenames).strip(", ").split(",")

            for filename in filenames:
                self._parse_file(filename)

        self._check_and_fix()

    def _check_and_fix(self):
        for gname, opts in self._opts.items():
            group = self._caches[gname]
            for name, opt in opts.items():
                if name in group:
                    continue
                elif opt[1] is not None or opt[0] == self._parse_bool:
                    self._set_group_opt(gname, name, opt[1])
                    continue

                if not self._allow_empty:
                    msg = "The option '{0}' in the group '{1}' has no value."
                    raise ValueError(msg.format(name, gname))

        # Set the options in the default group into self.
        group = self._caches.pop(self._default_group_name)
        for key, value in group.items():
            if key in self._caches:
                msg = "'{0}' had has the value '{1}'"
                raise ValueError(msg.format(self.__class__.__name__, key))
            self._caches[key] = value

    def _parse_file(self, filename):
        filename = str(filename)
        with open(filename) as f:
            lines = f.readlines()

        gname = self._default_group_name
        index, max_index = 0, len(lines)
        while index < max_index:
            line = self._parse_string(lines[index]).strip()
            index += 1

            # Comment
            if not line or line[0] in ("#", "=", ";"):
                continue

            # Group Section
            if line[0] == "[":
                if line[-1] != "]":
                    m = ("the format of the group is wrong, "
                         "which must start with [ and end with ]")
                    raise ValueError(m)
                _gname = line[1:-1]
                if not _gname:
                    raise ValueError("the group name is empty")
                if _gname not in self._caches:
                    continue
                gname = _gname
                continue

            # Group Option Values
            items = line.split("=", 1)
            if len(items) != 2:
                raise ValueError("the format is wrong, must contain '=': " + line)

            name, value = self._uniformize(items[0].strip()), items[1].strip()

            # Handle the continuation line
            if value[-1:] == "\\":
                values = [value.rstrip("\\").strip()]
                while index < max_index:
                    value = lines[index].strip()
                    values.append(value.rstrip("\\").strip())
                    index += 1
                    if value[-1:] != "\\":
                        break
                value = "\n".join(values)

            opt = self._opts[gname].get(name, None)
            if opt:
                self._set_group_opt(gname, name, opt[0](value))

    def register_bool(self, name, short=None, default=None, group=None, help=None):
        """Register the bool option.

        The value of this option will be parsed to the type of bool.
        """
        self._register(name, self._parse_bool, short=short, default=default,
                       group=group, help=help)

    def register_int(self, name, short=None, default=None, group=None, help=None):
        """Register the int option.

        The value of this option will be parsed to the type of int.
        """
        self._register(name, self._parse_int, short=short, default=default,
                       group=group, help=help)

    def register_float(self, name, short=None, default=None, group=None, help=None):
        """Register the float option.

        The value of this option will be parsed to the type of float.
        """
        self._register(name, self._parse_float, short=short, default=default,
                       group=group, help=help)

    def register_str(self, name, short=None, default=None, group=None, help=None):
        """Register the str option.

        The value of this option will be parsed to the type of str.
        """
        self._register(name, self._parse_string, short=short, default=default,
                       group=group, help=help)

    def register_int_list(self, name, short=None, default=None, group=None, help=None):
        """Register the int list option.

        The value of this option will be parsed to the type of int list.
        """
        self._register(name, self._parse_ints, short=short, default=default,
                       group=group, help=help)

    def register_str_list(self, name, short=None, default=None, group=None, help=None):
        """Register the string list option.

        The value of this option will be parsed to the type of string list.
        """
        self._register(name, self._parse_strings, short=short, default=default,
                       group=group, help=help)

    ###########################################################################
    # Parse CLI
    def parse(self, *args, **kwargs):
        return self.parse_cli(*args, **kwargs)

    def parse_cli(self, args=None, config_file_name="config-file"):
        """Parse the cli options."""
        if self._parsed:
            raise Exception("Have been parsed")
        self._parsed = True

        if args is None:
            args = sys.argv[1:]
        if not args:
            self._check_and_fix()
            return None

        gopts, args = self._parser_cli(args, description=self._description,
                                       config_file_name=config_file_name)
        if getattr(args, "version", False):
            print(self._version)
            sys.exit(0)

        if config_file_name:
            config_file = getattr(args, self._uniformize(config_file_name), "")
            for filename in config_file.split(","):
                filename = filename.strip()
                if filename:
                    self._parse_file(filename)

        for cli_opt, (gname, name) in gopts.items():
            opt = self._opts[gname][name]
            value = getattr(args, cli_opt, None)
            if value is not None:
                value = opt[0](value)
                if value != opt[1]:
                    self._set_group_opt(gname, name, value, force=True)

        self._check_and_fix()
        return args

    def _parser_cli(self, args, description=None, config_file_name=None):
        cli = ArgumentParser(description=description)
        if config_file_name:
            cli.add_argument("--" + config_file_name, default="",
                             help="The config file path.")
        cli.add_argument("--version", action="store_true",
                         help="Print the version and exit.")

        group_opts = {}
        for gname, opts in self._opts.items():
            if gname == self._default_group_name:
                group = cli
            else:
                group = cli.add_argument_group(gname)

            for name, (parser, default, help, short) in opts.items():
                action = None
                if parser == self._parse_bool:
                    action = "store_false" if default else "store_true"
                    default = False if default is None else default

                if gname == self._default_group_name:
                    opt_name = self._unniformize(name)
                    opt_key = self._uniformize(name)
                else:
                    opt_name = self._unniformize("{0}-{1}".format(gname, name))
                    opt_key = self._uniformize(opt_name)
                group_opts[opt_key] = (gname, name)
                short = "-" + short if short and short[0] != "-" else short
                names = [short, "--" + opt_name] if short else ["--" + opt_name]
                group.add_argument(*names, action=action, default=default, help=help)

        return group_opts, cli.parse_args(args=args)
