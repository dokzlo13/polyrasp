import inspect

from .command import CommandHandlers


class CommandsAliases:
    @staticmethod
    def alias_filter(value):
        def fun(message):
            return message.text == value
        return fun

    def log_wrapper(self, fun):
        def decor(message):
            # print("User {0} send {1}".format(message.from_user.id, message.text))
            return fun(message)
        return decor

    def __init__(self, command_handlers: CommandHandlers, *mappers: dict):
        if len(mappers) < 1:
            raise ValueError('Need to be setted almost one mapper for aliases')
        elif len(mappers) == 1:
            self.mapper = mappers[0]
        else:
            map_set = mappers[0].keys()
            for m in mappers[1:]:
                if any(map_set & m.keys()):
                    raise KeyError('Commads alias mappers cant have repeating keys!'
                                   ' Repeated: "{0}" from {1}'.format(map_set & m.keys(), m))
                map_set = map_set | m.keys()

            self.mapper = mappers[0]
            for m in mappers[1:]:
                self.mapper.update(m)

        for method in inspect.getmembers(command_handlers, predicate=inspect.ismethod):
            if method[0].startswith('_'):
                continue

            founded_alias = None
            for key in self.mapper:
                if method[0].startswith(key):
                    # name, func, alias
                    founded_alias = method[0], method[1], self.mapper[key]

            if founded_alias:
                print('Alias found for "{0}" -> "{2}"'.format(*founded_alias), )
                command_handlers._add_handler(founded_alias[1],
                                     commands=None,
                                     func=self.log_wrapper(self.alias_filter(founded_alias[2])),
                                     content_types=['text'],
                                     regexp=None
                                     )
            else:
                print('Alias NOT found for "{0}"'.format(method[0]))
