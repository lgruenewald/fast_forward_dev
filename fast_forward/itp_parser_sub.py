# Copyright 2020 University of Groningen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from vermouth.gmx.itp_read import ITPDirector
from vermouth.parser_utils import split_comments
from vermouth.molecule import Interaction

class FastForwardITPParser(ITPDirector):
    '''
    Same as the ITP parser but allows stashing of comments with interactions.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_comment = None

    def parse(self, file_handle):
        """
        Reads lines from `file_handle`, and calls :meth:`dispatch` to find
        which method to call to do the actual parsing. Yields the result of
        that call, if it's not `None`.
        At the end, calls :meth:`finalize`, and yields its results, iff
        it's not None.
        Parameters
        ----------
        file_handle: collections.abc.Iterable[str]
            The data to parse. Should produce lines of data.
        Yields
        ------
        object
            The results of dispatching to parsing methods, and of
            :meth:`finalize`.
        """
        lineno = 0
        for lineno, line in enumerate(file_handle, 1):
            line, comment = split_comments(line, self.COMMENT_CHAR)
            self.current_comment = comment
            if not line:
                continue
            result = self.dispatch(line)(line, lineno)

            if result is not None:
                yield result

        result = self.finalize(lineno)
        if result is not None:
            yield result

    def _base_parser(self, tokens, context, section, atom_idxs):
        """
        Converts an interaction line into a vermouth interaction
        tuple. It updates the block interactions in place.
        Parameters
        ----------
        tokens: collections.deque[str]
            Deque of token to inspect. The deque **can be modified** in place.
        context: :class:`vermouth.molecule.Block`
            The current block we parse
        section: str
            The current section header
        atom_idxs: list of ints or strings that are valid python slices
        """
        # split atoms and parameters

        atoms, parameters = self._split_atoms_and_parameters(tokens, atom_idxs)

        # perform check on the atom ids
        treated_atoms = self._treat_block_interaction_atoms(atoms, context, section)

        if self.current_meta:
            meta = {self.current_meta['condition']: self.current_meta['tag']}
        else:
            meta = {}

        if self.current_comment:
            meta['comment'] = self.current_comment

        interaction = Interaction(
            atoms=treated_atoms,
            parameters=parameters,
            meta=meta,)

        context.interactions[section] = context.interactions.get(section, []) + [interaction]

def read_itp(lines, force_field):
    director = FastForwardITPParser(force_field)
    return list(director.parse(iter(lines)))
