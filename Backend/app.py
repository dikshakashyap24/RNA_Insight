#!/usr/bin/env python
# coding=utf-8

import os
import copy
import itertools
import pandas as pd
import joblib
import matplotlib
matplotlib.use('Agg')
import datetime
from flask_cors import CORS, cross_origin

from flask import Flask, request, jsonify

app = Flask(__name__)
CORS(app)


# Function to count k-mer in each RNA sequence
def _count_kmer(Dataset, k):
    # copy dataset
    dataset = copy.deepcopy(Dataset)
    # alphbet of nucleotide
    nucleotide = ['A', 'C', 'G', 'T']

    # generate k-mers
    #  k == 5:
    five = list(itertools.product(nucleotide, repeat=5))
    pentamer = []
    for n in five:
        pentamer.append("".join(n))

    #  k == 4:
    four = list(itertools.product(nucleotide, repeat=4))
    tetramer = []
    for n in four:
        tetramer.append("".join(n))

    # k == 3:
    three = list(itertools.product(nucleotide, repeat=3))
    threemer = []
    for n in three:
        threemer.append("".join(n))

    # input features can be combinations of different k values
    if k == 34:
        table_kmer = dict.fromkeys(threemer, 0)
        table_kmer.update(dict.fromkeys(tetramer, 0))
    if k == 45:
        table_kmer = dict.fromkeys(tetramer, 0)
        table_kmer.update(dict.fromkeys(pentamer, 0))
    if k == 345:
        table_kmer = dict.fromkeys(threemer, 0)
        table_kmer.update(dict.fromkeys(tetramer, 0))
        table_kmer.update(dict.fromkeys(pentamer, 0))

    # count k-mer for each sequence
    for mer in table_kmer.keys():
        table_kmer[mer] = dataset["cdna"].apply(lambda x: x.count(mer))

    # for k-mer raw count without normalization
    rawcount_kmer_df = pd.DataFrame(table_kmer)
    df1_rawcount = pd.concat([rawcount_kmer_df, dataset["seq_id"]], axis=1)

    # for k-mer frequency with normalization
    freq_kmer_df = rawcount_kmer_df.apply(lambda x: x / x.sum(), axis=1)
    df1 = pd.concat([freq_kmer_df, dataset["seq_id"]], axis=1)

    return df1, df1_rawcount

# Load RNAlight model
def load_model():
    model_path = "static/RNALightModel.pkl"
    return joblib.load(model_path)

# Data Processing
def process_data(query_file, tmp_dir, outputdir, prefix, RNA):
    app.logger.info("Converting Fasta to TSV...")
    tab_tmp = prefix + ".txt"
    if RNA:
        fa2tab = f"seqkit seq --dna2rna {query_file} | seqkit fx2tab | awk '{{print $1\"\t\"toupper($2)}}' > {os.path.join(tmp_dir, tab_tmp)}"
    else:
        fa2tab = f"seqkit fx2tab {query_file} | awk '{{print $1\"\t\"toupper($2)}}' > {os.path.join(tmp_dir, tab_tmp)}"
    app.logger.info("Converted Fasta to TSV...")

    os.system(fa2tab)
    str_temp = os.path.join(tmp_dir, tab_tmp)
    app.logger.info(f"Temp Path: {str_temp}")
    query = pd.read_csv(os.path.join(tmp_dir, tab_tmp), sep='\t', index_col=False, names=["seq_id", "cdna"])
    df_kmer_345, df_kmer_345_rawcount = _count_kmer(query, 345)

    kmer_file = prefix + "_df_kmer345_freq.tsv"
    kmer_rowcount_file = prefix + "_df_kmer345_rawcount.tsv"
    df_kmer_345.to_csv(os.path.join(outputdir, kmer_file), sep='\t')
    df_kmer_345_rawcount.to_csv(os.path.join(outputdir, kmer_rowcount_file), sep='\t')

    return df_kmer_345, query, kmer_file, kmer_rowcount_file

# Predict
def predict(df_kmer_345, RNA_Light, outputdir, prefix, query, kmer_file, kmer_rowcount_file):
    del df_kmer_345['seq_id']
    x_kmer = df_kmer_345.values

    y_pred = RNA_Light.predict(x_kmer)
    y_prob = RNA_Light.predict_proba(x_kmer)[:, 1]

    query["RNALight_pred_label"] = y_pred
    query["RNALight_pred_prob"] = y_prob
    query["Light_score"] = 2 * y_prob - 1

    outputfile = prefix + "_RNAlight_predict_df.txt"
    # query.to_csv(os.path.join(outputdir, outputfile), sep='\t', index=False)

    # Delete the files after use
    os.remove(os.path.join(outputdir, kmer_file))
    os.remove(os.path.join(outputdir, kmer_rowcount_file))

    return query

@app.route('/upload', methods=['POST'])
@cross_origin()
def upload_file():
    file_name = request.files['file']
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    # Save the uploaded file
    upload_dir = os.path.join(os.getcwd(), "uploaded_files")
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    # Append timestamp to the filename
    try:
        filename, extension = os.path.splitext(file.filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{filename}_{timestamp}{extension}"
        file_path = os.path.join(upload_dir, new_filename)
        file.save(file_path)
    except Exception as E:
        return jsonify({'error': E})


    return jsonify({'message': 'File uploaded successfully', 'file_path': file_path, 'code': '201'})

@app.route('/predict', methods=['POST'])
@cross_origin()
def perform_prediction():
    # Load model
    app.logger.info("Loading model...")
    RNA_Light = load_model()
    app.logger.info("Model Loaded")


    # Load uploaded file
    file_path = request.json.get('file_path')
    app.logger.info(f"Reading File from path {file_path}")
    if file_path is None:
        app.logger.error("No file path provided")
        return jsonify({'error': 'File path not provided'})
    app.logger.info("File Loaded...")


    # Data processing
    app.logger.info("Data Processing started...")
    tmp_dir = os.path.join(os.path.dirname(file_path), "tmp")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    try:
        df_kmer_345, query, kmer_file, kmer_rowcount_file = process_data(file_path, tmp_dir, os.path.dirname(file_path), file_path, True)
    except Exception as e:
        app.logger.error("Error", e)
        return jsonify({'message': 'Internal Server Error'})
    app.logger.info("Data Processing over...")


    # Prediction
    prediction_result = predict(df_kmer_345, RNA_Light, os.path.dirname(file_path), file_path, query, kmer_file, kmer_rowcount_file)
    # Convert DataFrame to dictionary
    prediction_dict = prediction_result.to_dict(orient='records')

    return jsonify({'message': prediction_dict})

@app.route('/status', methods=['GET'])
@cross_origin()
def check_status():
    return jsonify({'status': 'API is up and running'})


if __name__ == '__main__':
    app.run(debug=True)

