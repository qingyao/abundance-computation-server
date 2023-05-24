from computeAbundanceApp import app
from flask import request, send_file, session
from werkzeug.utils import secure_filename
import os, uuid
import subprocess as sbp
app_dir = 'computeAbundanceApp'

@app.route('/upload', methods=['POST'])
def upload_file():
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

        filename = secure_filename(file.filename)
        
        for l in file:
            if len(l.decode('utf8').split('\t')) != 2:
                return 'Wrong file format', 400
            break
        file_path = os.path.join(user_directory,filename)
        file.save(file_path)
        print('File saved successfully.')

        p = sbp.run(f"python3 {app_dir}/scripts/ComputeAbundanceswithSC.py -s {file_path} -f {app_dir}/test/9606.protein.sequences.v11.5.fa > {file_path+'.out'}", 
                shell=True)
        if p.returncode == 0:
            return send_file(file_path+'.out', as_attachment=True)
        

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=os.getenv('PORT'), debug=True)
 

