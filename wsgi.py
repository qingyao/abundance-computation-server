from computeAbundanceApp import app
from flask import request, send_file, session
from werkzeug.utils import secure_filename
import os, uuid
from pathlib import Path
import subprocess as sbp

app_dir = 'computeAbundanceApp'
aminoAcids = set(list('ARNDCQEGHILKMFPSTWYV'))
known_species_ids = set()
with open(os.path.join(app_dir, 'rsc', 'species_ids.txt')) as f:
    for l in f:
        known_species_ids.add(int(l))

@app.route('/upload_sc', methods=['POST'])
def upload_sc():
    # check if the post request has the file part
    if 'file' not in request.files:
        return 'No file part in the request.', 400
    file = request.files['file']
    # if user does not select file, file variable will be empty
    if file.filename == '':
        return 'No selected file.', 400
    # generate unique session id if not already done
    if 'uuid' not in session:
        session['uuid'] = str(uuid.uuid4())
    # create user directory based on session id if not exist
    
    if file:
        user_directory = os.path.join(app_dir, 'user_upload', session['uuid'])
        os.makedirs(user_directory, exist_ok=True)

        filename = 'user.sc'
        file_path = os.path.join(user_directory,filename)
        file.save(file_path)

        with open(file_path, 'r') as f:
            for i, l in enumerate(f):
                if len(l.split('\t')) != 2:
                    return 'File needs to be in 2-column tab-delimited format', 400
                ll = l.split('\t')
                if not all([i in aminoAcids for i in ll[0]]):
                    return f'Line {i+1}: Invalid amino acid', 400
                try:
                    float(ll[1])
                except ValueError:
                    return f'Line {i+1}: Invalid quantity value', 400
                
        return 'File saved successfully.', 200

@app.route('/upload_fasta', methods=['POST'])
def upload_fasta():
    # check if the post request has the file part
    if 'file' not in request.files:
        return 'No file part in the request.', 400
    file = request.files['file']
    # if user does not select file, file variable will be empty
    if file.filename == '':
        return 'No selected file.', 400
    # generate unique session id if not already done
    if 'uuid' not in session:
        session['uuid'] = str(uuid.uuid4())
    
    if file:
        user_directory = os.path.join(app_dir, 'user_upload', session['uuid'])
        os.makedirs(user_directory, exist_ok=True)

        filename = 'user.fa'
        file_path = os.path.join(user_directory,filename)

        if os.path.islink(file_path) or os.path.isfile(file_path):
            os.remove(file_path)


        file.save(file_path)
        return 'File saved successfully.', 200
    else:
        return 'Upload unsuccessful', 400

@app.route('/spid_check', methods = ['POST'])
def check_id():
    if 'uuid' not in session:
        session['uuid'] = str(uuid.uuid4())
    
    spid = request.form.get('spid')
    
    if int(spid) in known_species_ids:
        user_directory = os.path.join(app_dir, 'user_upload', session['uuid'])
        os.makedirs(user_directory, exist_ok=True)
    
        ## download fasta file if not already exists in rsc/fasta/
       
        dest = f'{app_dir}/rsc/fasta/{spid}.protein.sequences.v11.5.fa'
        if not os.path.isfile(dest):
            src = f'{app_dir}/rsc/fasta/{spid}.protein.sequences.v11.5.fa.gz'
            p = sbp.run(f"wget -O {src} https://stringdb-static.org/download/protein.sequences.v11.5/{spid}.protein.sequences.v11.5.fa.gz;gunzip {src}",
                        shell=True)

        filename = 'user.fa'
        file_path = os.path.join(user_directory,filename)
        if os.path.islink(file_path) or os.path.isfile(file_path):
            os.remove(file_path)

        Path(file_path).symlink_to(Path(f"{app_dir}/rsc/fasta/{spid}.protein.sequences.v11.5.fa").resolve())
        return "Found fasta file can compute now"
    else:
        return "Please upload custom fasta file"


@app.route('/submit', methods=['POST'])
def compute():
    user_directory = os.path.join(app_dir, 'user_upload', session['uuid'])
    
    p = sbp.run(f"python3 {app_dir}/scripts/ComputeAbundanceswithSC.py -s {user_directory}/user.sc -f {user_directory}/user.fa > {user_directory}/user.out", 
            shell=True, capture_output=True)
    
    if p.returncode == 0:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return send_file(f'{base_dir}/{user_directory}/user.out', as_attachment=True)
    else:
        if p.stderr:
            return p.stderr.decode('utf-8')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=os.getenv('PORT'), debug=True)
 

