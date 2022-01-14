# Copyright 2021 University of Groningen
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
from collections import defaultdict
import numpy as np
import MDAnalysis as mda
from MDAnalysis import transformations


def dim2lattice(x, y, z, alpha=90, beta=90, gamma=90):
    """
    Convert dimensions (lengths/angles) to lattice matrix
    """
    cosa = np.cos( np.pi * alpha / 180 )
    cosb = np.cos( np.pi * beta / 180 )
    cosg = np.cos( np.pi * gamma / 180 )
    sing = np.sin( np.pi * gamma / 180 )

    zx = z * cosb
    zy = z * ( cosa - cosb * cosg ) / sing
    zz = np.sqrt( z**2 - zx**2 - zy**2 )

    return np.array([x, 0, 0, y * cosg, y * sing, 0, zx, zy, zz]).reshape((3,3))


class UniverseHandler(mda.Universe):
    """
    Wrapper around mda.Universe which allows for
    some smart selections and exposes some useful
    properties.
    """
    def __init__(self, mol_names, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # select which molecules to treat
        self.mol_names = mol_names
        self.molecules = self.select_atoms("moltype " + " ".join(mol_names))

        # set some useful attributes
        self.mol_idxs_by_name = defaultdict(list)
        for mol_num, mol_name in dict(zip(self.atoms.molnums, self.atoms.moltypes)).items():
            if mol_name in mol_names:
                self.mol_idxs_by_name[mol_name].append(mol_num)

        mol_idxs_names = [(idx, mol_name) for idx, mol_name in self.mol_idxs_by_name.items()]
        self.normal_order = mol_idxs_names.sort()

        istraj = args[1].casefold().endswith(('trr', 'xtc'))
        
        # Required for unwrapping
        if istraj:
            self.pbc = np.array([ dim2lattice(*f.dimensions) for f in self.trajectory ])
            self.coordinates = self.trajectory.coordinate_array.astype('float64')
        else:
            self.pbc = dim2lattice(*self.dimensions)[None]
            self.coordinates = self.atoms.positions[None].astype('float64')
            
        self.ipbc = 2 * np.pi * np.linalg.inv(self.pbc) 
        self.reciprocal = (self.coordinates @ self.ipbc)
        
        # Hidden attribute labels
        self.__n_atoms = None
        self.__n_residues = None
        self.__pbc_completed = False
        self.__resids = None

    @property
    def n_atoms(self):
        if self.__n_atoms is None:
            self.__n_atoms = len(self.molecules)
        return self.__n_atoms

    @property
    def resids(self):
        if self.__resids is None:
            self.__resids = self.molecules.resids
        return self.__resids

    @property
    def n_residues(self):
        if self.__n_residues is None:
            self.__n_residues = len(self.molecules.residues)
        return self.__n_residues

    def res_iter(self):
        for residue in self.molecules.residues:
            yield residue
