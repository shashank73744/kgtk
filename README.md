<img src="https://github.com/usc-isi-i2/kgtk/raw/master/docs/images/kgtk_logo_200x200.png" width="150"/>

# KGTK: Knowledge Graph Toolkit 

[![doi](https://zenodo.org/badge/DOI/10.5281/zenodo.3828068.svg)](https://doi.org/10.5281/zenodo.3828068)  ![travis ci](https://travis-ci.org/usc-isi-i2/kgtk.svg?branch=master)  [![Coverage Status](https://coveralls.io/repos/github/usc-isi-i2/kgtk/badge.svg?branch=master)](https://coveralls.io/github/usc-isi-i2/kgtk?branch=master)

KGTK is a Python library for easy manipulation with knowledge graphs. It provides a flexible framework that allows chaining of common graph operations, such as: extraction of subgraphs, filtering, computation of graph metrics, validation, cleaning, generating embeddings, and so on. Its principal format is TSV, though we do support a number of other inputs. 

## Features

* Computation of reachable nodes
* Filtering based on property values
* Removal of columns
* Sorting
* Computation of embeddings
* Cleaning and validation
* Computation of graph metrics
* Joining and concatenation of graphs
* Manipulation of Wikidata data

## Getting started

### Documentation

https://kgtk.readthedocs.io/en/latest/

### Demo: try KGTK online with MyBinder
The easiest, no-cost way of trying out KGTK is through [MyBinder](https://mybinder.org/). We have made available several **example notebooks** to show some of the features of KGTK, which can be run in two environments: 

* Basic KGTK functionality: This notebook may take 5-10 minutes to launch, please be patient. Note that in this notebook some KGTK commands (graph analytics and embeddings) **will not run**. To launch the notebook in your browser, click on the "Binder" icon: [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/usc-isi-i2/kgtk/dev?filepath=examples%2FExample5%20-%20AIDA%20AIF.ipynb)

* Advanced KGTK functionality: This notebook may take 10-20 minutes to launch. It includes basic KGTK functionality and **graph analytics and embedding capabilities** of KGTK:  [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/dgarijo/kgtk/dev?filepath=%2Fkgtk%2Fexamples%2FCSKG%20Use%20Case.ipynb)

For executing KGTK with large datasets, **we recommend a Docker/local installation**.

### KGTK notebooks

The [examples folder](examples/) provides a larger and constantly increasing number of easy-to-follow Jupyter Notebooks which showcase different functionalities of KGTK. These include computing:
* Embeddings for ConceptNet nodes
* Graph statistics over a curated subset of Wikidata
* Reachable occupations for selected people in Wikidata
* PageRank over Wikidata
* etc.

## Installation

### Releases

* [Source code](https://github.com/usc-isi-i2/kgtk/releases)


### Installation through Docker

```
docker pull uscisii2/kgtk
```

To run KGTK in the command line just type:

```
docker run -it uscisii2/kgtk /bin/bash
```

If you want to run KGTK in a **Jupyter notebook**, then you will have to type:
```
docker run -it -p 8888:8888 uscisii2/kgtk:latest /bin/bash -c "jupyter notebook --ip='*' --port=8888 --no-browser"
```
Versions 0.3.2 and 0.2.1 require `--allow-root` as part of the jupyter notebook command.

Note: if you want to load data from your local machine, you will need to [mount a volume](https://docs.docker.com/storage/volumes/).

More information about versions and tags is available here: https://hub.docker.com/repository/docker/uscisii2/kgtk

See additional examples in [the documentation](https://kgtk.readthedocs.io/en/latest/install/).

### Local installation

0. Our installations will be in a conda environment. If you don't have a conda installed, follow [link](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) to install it.
1. Set up your own conda environment:
```
conda create -n kgtk-env python=3.7
conda activate kgtk-env
```
 **Note:** Installing Graph-tool is problematic on python 3.8 and out of a virtual environment. Thus: **the advised installation path is by using a virtual environment.**

2. Install (the dev branch at this point): `pip install kgtk`

You can test if `kgtk` is installed properly now with: `kgtk -h`.

3. Download the English model of SpaCY: `python -m spacy download en_core_web_sm`

4. Install `graph-tool`: `conda install -c conda-forge graph-tool`. If you don't use conda or run into problems, see these [instructions](https://git.skewed.de/count0/graph-tool/-/wikis/installation-instructions). 

### Updating your KGTK installation
To update your version of KGTK, just follow the instructions below:

- If you installed KGTK with through Docker, then just pull the most recent image: `docker pull <image_name>`, where `<image_name>` is the tag of the image of interest (e.g. uscisii2/kgtk:latest)
- If you installed KGTK from pip, then type `pip install -U kgtk`.
- If you installed KGTK from GitHub, then type `git pull && pip install` . Alternatively, you may execute:  `git pull && python setup.py install`. 
- If you installed KGTK in development mode, (i.e., `pip install -e`); then you only need to do update your repository: `git pull`.

## Running KGTK commands

To list all the available KGTK commands, run:

```
kgtk -h
```

To see the arguments of a particular commands, run:

```
kgtk <command> -h
```

An example command that computes instances of the subclasses of two classes:

```
kgtk instances --transitive --class Q13442814,Q12345678
```

## Running unit tests locally
```
cd kgtk/tests
python -W ignore -m unittest discover
```

## How to cite

```
@article{ilievski2020kgtk,
  title={KGTK: A Toolkit for Large Knowledge Graph Manipulation and Analysis},
  author={Ilievski, Filip and Garijo, Daniel and Chalupsky, Hans and Divvala, Naren Teja and Yao, Yixiang and Rogers, Craig and Li, Ronpeng and Liu, Jun and Singh, Amandeep and Schwabe, Daniel and Szekely, Pedro},
  journal={arXiv preprint arXiv:2006.00088},
  year={2020},
  url={https://arxiv.org/abs/2006.00088}
}
```
