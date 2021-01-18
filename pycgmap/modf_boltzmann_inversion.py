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
import numpy as np
from .linalg_functions import vector_angle_degrees, dihedral_angle

def _vector_angle_matrix(matrix_a, matrix_b):
    for v1, v2 in zip(matrix_a, matrix_b):
        yield vector_angle_degrees(v1, v2)

def _dihedral_angle_matrix(matrix_a, matrix_b, matrix_c):
    for v1, v2, v3 in zip(matrix_a, matrix_b, matrix_c):
        yield dihedral_angle(v1, v2, v3)

def _bond_distance_matrix(matrix_a):
    for v1 in matrix_a:
        yield np.linalg.norm(v1)

NORMAL_FUNCS = {"angles": _vector_angle_matrix,
                "bonds": _bond_distance_matrix,
                "constraints": _bond_distance_matrix,
                "dihedrals": _dihedral_angle_matrix
               }

def modf_blotzmann_inversion(inter_type, interaction, distances, temp=298.15, gas_const=8.314):
    """
    Performs a modfied Boltzmann inversion as discribed in
    JA Graham in JCIM 2017. Distances is a numpy array of
    pair distances over a trajectory. Inter_type is the type of
    the interaction at hand. This procedure only supports
    bonds, angles, and constraints of types 1 and 2. Interaction
    is a interaction tuple describing the interaction. Note that
    this function assumes normal order of the pairs. This ..

    Parameters:
    -----------
    inter_type: str
        One of bonds, angles, constraints
    interaction: :type:`vermouth.molecule.Interaction`
        Named tuple describing the interaction
    distances: :class:np.ndarray[n_frames, n_pairs, 3]
        Array of pair distances. Note that the atoms
        order of pairs needs to be the same as the order
        of the atom indices in the Interaction tuple

    Returns:
    --------
    :type:`vermouth.molecule.Interaction`
    """
    # compute RT
    const = temp * gas_const
    # compute pair vectors and make distribution
    func_type = interaction.parameters[0]
    if inter_type == 'bonds' or inter_type == "constraints":
        vectors = [distances[:, 0, :]]
    elif inter_type == "angles":
        vectors =  [distances[:, 0, :], distances[:, 1, :]]
    elif inter_type == "dihedrals":
        vectors = [distances[:, 0, :], distances[:, 1, :], distances[:, 2, :]]

    time_series = np.fromiter(NORMAL_FUNCS[inter_type](*vectors), dtype=float)
    filename = inter_type + "-" + str(func_type) + "_" + "_".join(map(str, list(interaction.atoms))) + ".xvg"
    np.savetxt(filename, time_series)
    # all normal ordered functions which are cosine harmonic
    # have interaction type 2
    avg = np.average(time_series)
    if func_type == "1" and inter_type == "angles":
        time_series = np.deg2rad(time_series)
        sig = np.std(time_series)
        k = const/(sig**2.*np.sin(np.deg2rad(avg))**2.0)

    elif func_type == "2" and inter_type == "bonds":
        sig = np.std(time_series)
        k = const/(sig**2.*np.sin(avg)**2.0)

    if func_type == "2" and inter_type == "angles":
        time_series = np.deg2rad(time_series)
        sig = np.std(time_series)
        k = const/(sig**2.*np.sin(np.deg2rad(avg))**2.0)
    else:
        sig = np.std(time_series)
        k = const/sig**2.

    # constraints don't get a force constant
    if inter_type == "constraints":
        interaction.parameters[:] = [func_type, avg]
    elif inter_type == "dihedrals":
        interaction.parameters[:] = [func_type, "not implemented"]
    else:
        interaction.parameters[:] = [func_type, avg, k]

    return interaction
