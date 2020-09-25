#! /bin/bash

# This script expects to be executed with the current working directory:
#
# kgtk/datasets/time-machine-20101201
source common.sh

# ==============================================================================
# Setup working directories:
mkdir --verbose ${DATADIR}
mkdir --verbose ${LOGDIR}


# ==============================================================================
# Import the Wikidata dump file, getting labels, aliases, and descriptions
# in all languages.
echo -e "\nImporting ${WIKIDATA_ALL_JSON} with labels, etc. in all languages"
kgtk ${KGTK_FLAGS} \
     import-wikidata \
     -i ${WIKIDATA_ALL_JSON} \
     --node ${DATADIR}/${WIKIDATA_ALL_NODES}.tsv \
     --edge ${DATADIR}/${WIKIDATA_ALL_EDGES}.tsv \
     --qual ${DATADIR}/${WIKIDATA_ALL_QUALIFIERS}.tsv \
     --node-file-id-only \
     --explode-values False \
     --all-languages \
     --alias-edges True \
     --split-alias-file ${DATADIR}/${WIKIDATA_ALL}-aliases-all-lang.tsv \
     --split-en-alias-file ${DATADIR}/${WIKIDATA_ALL}-aliases-en-only.tsv \
     --description-edges True \
     --split-description-file ${DATADIR}/${WIKIDATA_ALL}-descriptions-all-lang.tsv \
     --split-en-description-file ${DATADIR}/${WIKIDATA_ALL}-descriptions-en-only.tsv \
     --label-edges True \
     --split-label-file ${DATADIR}/${WIKIDATA_ALL}-labels-all-lang.tsv \
     --split-en-label-file ${DATADIR}/${WIKIDATA_ALL}-labels-en-only.tsv \
     --datatype-edges True \
     --split-datatype-file ${DATADIR}/${WIKIDATA_ALL}-datatypes.tsv \
     --entry-type-edges True \
     --split-type-file ${DATADIR}/${WIKIDATA_ALL}-types.tsv \
     --split-sitelink-file ${DATADIR}/${WIKIDATA_ALL}-sitelinks-all-lang.tsv \
     --split-en-sitelink-file ${DATADIR}/${WIKIDATA_ALL}-sitelinks-en-only.tsv \
     --use-kgtkwriter True \
     --use-shm True \
     --procs 5 \
     --mapper-batch-size 5 \
     --max-size-per-mapper-queue 10 \
     --single-mapper-queue True \
     --collect-results True \
     --collect-seperately True\
     --collector-batch-size 10 \
     --collector-queue-per-proc-size 15 \
     --progress-interval 500000 \
    |& tee ${LOGDIR}/import-split-wikidata.log
