from computeAbundanceApp import app
from flask import request, send_file, session, jsonify
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

@app.route('/api/upload_sc', methods=['POST'])
def upload_sc():
    
    # generate unique session id if not already done
    if 'session_id' not in session:
        session.permanent = True
        session['session_id'] = str(uuid.uuid4())
    
    # if user does not select file, file variable will be empty
    for fname in request.files: ## only get one file
        # print(fname)
        file = request.files.get(fname)
        # create user directory based on session id if not exist
        if file:
            
            user_directory = os.path.join(app_dir, 'user_upload', session['session_id'], 'in')
            os.makedirs(user_directory, exist_ok=True)

            file_path = os.path.join(user_directory, secure_filename(fname))
            file.save(file_path)

            with open(file_path, 'r') as f:
                try:
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
                except:
                    return 'Unknown file type', 400
                    
            return 'File saved successfully.', 200
            

@app.route('/api/upload_fa', methods=['POST'])
def upload_fasta():
    # generate unique session id if not already done
    if 'session_id' not in session:
        session.permanent = True
        session['session_id'] = str(uuid.uuid4())

    for fname in request.files: ## only get one file
        # print(fname)
        file = request.files.get(fname)
        if file:
            user_directory = os.path.join(app_dir, 'user_upload', session['session_id'])
            os.makedirs(user_directory, exist_ok=True)

            filename = 'user.fa'
            file_path = os.path.join(user_directory,filename)

            if os.path.islink(file_path) or os.path.isfile(file_path):
                os.remove(file_path)


            file.save(file_path)
            return 'File saved successfully.', 200
        else:
            return 'Upload unsuccessful', 400

@app.route('/api/spid_check', methods = ['POST'])
def check_id():
    if 'session_id' not in session:
        session.permanent = True
        session['session_id'] = str(uuid.uuid4())
    
    spid = request.form.get('spid')
    
    if int(spid) in known_species_ids:
        user_directory = os.path.join(app_dir, 'user_upload', session['session_id'])
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
        return "Found fasta file can compute now", 200
    else:
        return "Please upload custom fasta file", 400


@app.route('/api/submit', methods=['POST'])
def compute():
    
    user_directory = os.path.join(app_dir, 'user_upload', session['session_id'])
    
    for fname in os.listdir(f'{user_directory}/in'): ## should be one file only
        fname_out = os.path.splitext(fname)[0]+'.abu'
        p = sbp.run(f"python3 {app_dir}/scripts/ComputeAbundanceswithSC.py -s {user_directory}/in/{fname} -f {user_directory}/user.fa > {user_directory}/{fname_out}", 
                shell=True, capture_output=True)
        
        if p.returncode == 0:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
            return send_file(f'{base_dir}/{user_directory}/{fname_out}', as_attachment=True)
        else:
            if p.stderr:
                return p.stderr.decode('utf-8')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=os.getenv('PORT'), debug=True)
 

