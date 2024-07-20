import React, { useState } from 'react';
import LoadingBar from "react-top-loading-bar";
import './App.css'; // Import CSS file

function App() {
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [predictions, setPredictions] = useState([]);
  const [filePath, setFilePath] = useState('');
  const [progress, setProgress] = useState(0);


  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.name.endsWith('.fa')) {
      setFile(selectedFile);
      setFileError(false);
    } else {
      setFile(null);
      setFileError(true);
    }
  };

  const uploadFile = () => {
    if (file) {
      const formData = new FormData();
      formData.append('file', file);
      setProgress(30);
      fetch('http://127.0.0.1:5000/upload', {
        method: 'POST',
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        console.log(data);
        setUploadSuccess(true);
        setFilePath(data.file_path);
        setProgress(30);
      })
      .catch(error => console.error('Error:', error));
    } else {
      setFileError(true);
    }
  };

  const predict = () => {
    if (file) {
      fetch('http://127.0.0.1:5000/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ file_path: filePath }) // Use stored file path
      })
      .then(response => response.json())
      .then(data => {
        console.log(data);
        setPredictions(data.message);
      })
      .catch(error => console.error('Error:', error));
    } else {
      setFileError(true);
    }
  };

  return (
    <div className="container">
      <h1 className="title">RNA Light Predictor</h1>
      {uploadSuccess ? (
        <div className="button-container">
          <button className="upload-button" onClick={() => setUploadSuccess(false)}>Upload Again</button>
          <button onClick={predict}>Predict</button>
        </div>
      ) : (
          <div>
            <input type="file" accept=".fa" onChange={handleFileChange} className="file-input"/>
            <br/>
            <button onClick={uploadFile}>Upload</button>
            <p className="upload-text">Upload only cDNA files</p>
            {fileError && <p className="error-message">Please select a .fa file.</p>}
          </div>
      )}

      {predictions.length > 0 && (
          <div className="predictions-container">
          <h2>Predictions</h2>
          <table className="predictions-table">
            <thead>
              <tr>
                <th className="table-header-cell">Sequence ID</th>
                <th className="table-header-cell">Probability</th>
                <th className="table-header-cell">Prediction Label</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((prediction, index) => (
                <tr key={index}>
                  <td className="table-cell">{prediction.seq_id}</td>
                  <td className="table-cell">{prediction.RNALight_pred_prob}</td>
                  <td className="table-cell">{prediction.RNALight_pred_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;
