from prompt_toolkit import PromptSession, HTML
import json
import os

from prompt_toolkit.completion import Completer, Completion
from logging import info


class CategoryManager:
    UNCATEGORIZED_ACCOUNT = 'Unspecified'

    def __init__(self, lookup_file, categories_list):
        self.lookup_file = lookup_file
        self.lookup_data = self.load_lookup_data()
        self.categories_list = categories_list

    def load_lookup_data(self):
        if not os.path.exists(self.lookup_file):
            self.create_new_lookup_file()

        with open(self.lookup_file, 'r') as file:
            return json.load(file)

    def create_new_lookup_file(self):
        category_lookup = {}
        for category in self.categories_list:
            category_lookup[category] = []
        with open(self.lookup_file, 'w') as json_file:
            json.dump(category_lookup, json_file, indent=4)

    def update_lookup(self, category, pattern, match_type):
        if category not in self.lookup_data:
            self.lookup_data[category] = []

        exists = any(entry['payee'] == pattern for entry in self.lookup_data[category])
        if not exists:
            self.lookup_data[category].append({'payee': pattern, 'type': match_type})
            self.save_lookup_data()
            info(f'Added {match_type} pattern: [{pattern}] for category: {category}')

    def save_lookup_data(self):
        with open(self.lookup_file, 'w') as file:
            json.dump(self.lookup_data, file, indent=4)
        info(f'Lookup file updated: {self.lookup_file}')

    def category_prompt(self):
        category_prompt_message = HTML(
            '<style fg="ansigreen">Enter a category for '
            "this transaction\'s payee (or press Enter to mark "
            f'as "{CategoryManager.UNCATEGORIZED_ACCOUNT}") ></style> '
        )

        return PromptSession(
            search_ignore_case=True,
            completer=CategoryCompleter(self.categories_list),
            message=category_prompt_message,
        )

    def pattern_prompt(self):
        pattern_prompt_message = HTML(
            '<style fg="ansigreen">Enter a /pattern/ or string to match '
            'future payees for this category, Enter a /pattern/ or string to match '
            'future payees for this category, enter a string for case insensitive '
            'substring match, or leave blank to skip ></style> '
        )

        return PromptSession(message=pattern_prompt_message)


# Custom completer for hierarchical categories
class CategoryCompleter(Completer):
    '''
    Initialize the CategoryCompleter with a list of categories.

    Args:
        categories (list): A list of category names for completion.
    '''

    def __init__(self, categories):
        self.categories = categories
        self.categories.sort()

    def get_completions(self, document, complete_event):
        '''
        Provide completion suggestions based on user input.

        Args:
            document (Document): The document containing the current input.
            complete_event (CompleteEvent): The event triggering the completion.

        Yields:
            Completion: A completion suggestion for the input.
        '''
        text = document.text_before_cursor.lower()
        for category in self.categories:
            if category.lower().startswith(text):
                yield Completion(category, start_position=-len(text))
