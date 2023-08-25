from computeAbundanceApp import app
from flask import request, send_file, session, jsonify, render_template, make_response
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import subprocess as sbp
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator
from Bio import SeqIO
import shutil
import zipfile

app_dir = 'computeAbundanceApp'

aminoAcids = set(list('ARNDCQEGHILKMFPSTWYV'))
known_species_ids = set()
base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(app_dir, 'rsc', 'species_ids.txt')) as f:
    for l in f:
        known_species_ids.add(int(l))


def is_valid_fasta(filename):
    try:
        count = 0
        with open(filename, "r") as file:
            for i, record in enumerate(SeqIO.parse(file, "fasta")):
                # Check if each sequence has an ID and sequence data
                count += 1
                if not record.id or not record.seq:
                    return False, f'Record {i+1} does not contain ID or Sequence.'
            if count < 50:
                return False, "Fewer than 50 fasta records present."
        return True, "Success"
    except:
        return False, "Could not parse uploaded file as fasta."

def clean_up_uploaded(session_id, fname='all'):
    user_directory = os.path.join(app_dir, 'user_upload', session_id, 'in')
    if os.path.isfile(os.path.join(user_directory, fname)):
        os.remove(os.path.join(user_directory, fname))

def clean_up_computed(session_id, fname='all'):
    
    out_dir = os.path.join(app_dir, 'user_upload', session_id, 'out')
    status_dir = os.path.join(app_dir, 'user_upload', session_id, 'status')
    error_dir = os.path.join(app_dir, 'user_upload', session_id, 'error')
    
    if os.path.isdir(out_dir):
        for f in os.listdir(out_dir):
            if fname=='all':
                os.remove(os.path.join(out_dir, f))
            elif os.path.splitext(f)[0] == os.path.splitext(fname)[0]:
                os.remove(os.path.join(out_dir, f))

    if os.path.isdir(status_dir):
        if os.path.isfile(os.path.join(status_dir,'status.all')):
            os.remove(os.path.join(status_dir,'status.all'))
        for f in os.listdir(status_dir):
            if fname=='all':
                os.remove(os.path.join(status_dir, f))
            elif os.path.splitext(f)[0] == os.path.splitext(fname)[0]:
                os.remove(os.path.join(status_dir, f))
    
    if os.path.isdir(error_dir):
        
        for f in os.listdir(error_dir):
            if fname=='all':
                os.remove(os.path.join(error_dir, f))
            elif os.path.splitext(f)[0] == os.path.splitext(fname)[0]:
                os.remove(os.path.join(error_dir, f))
    

@app.route('/api/remove_sc', methods = ['POST'])
def remove_sc():
    session_id = request.headers.get('X-Session-ID')
    
    data = request.get_json()
    fname = secure_filename(data.get('fname'))
    clean_up_uploaded(session_id, fname)
    clean_up_computed(session_id, fname)
    
    return 'File removed', 200
    
@app.route('/api/remove_fa', methods = ['GET'])
def remove_fa():
    session_id = request.headers.get('X-Session-ID')
    f2rm = os.path.join(app_dir, 'user_upload', session_id, 'user.fa')
    if os.path.isfile(f2rm):
        os.remove(f2rm)
        return 'File removed', 200
    return 'File not found', 200

def write_error_file(content, dirname, fstem):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with open(os.path.join(dirname, fstem+'.error'), 'w') as wf:
        print(content, file = wf)

@app.route('/api/upload_sc', methods=['POST'])
def upload_sc():
    session_id = request.headers.get('X-Session-ID')
    user_directory = os.path.join(app_dir, 'user_upload', session_id, 'in')
    remove_directory = os.path.join(app_dir, 'user_upload', session_id, 'remove')
    os.makedirs(user_directory, exist_ok=True)

    # if user does not select file, file variable will be empty
    for fname in request.files: 
        # print(fname)
        file = request.files.get(fname)
        
        # create user directory based on session id if not exist
        if file:
            
            file_path = os.path.join(user_directory, secure_filename(fname))
            file.save(file_path)
            fstem = os.path.splitext(secure_filename(fname))[0]
            if os.path.isfile(os.path.join(remove_directory, fstem+'.error')):
                os.remove(os.path.join(remove_directory, fstem+'.error'))

            with open(file_path, 'r') as f:
                try:
                    for i, l in enumerate(f):
                        if len(l.split('\t')) != 2:
                            message = 'File error: file needs to be in 2-column tab-delimited format'
                            write_error_file(message, remove_directory, fstem)
                            os.remove(file_path)
                            return message, 404

                except Exception as e:
                    message = 'File reading error' 
                    if e:
                        message += f': {e}'
                    write_error_file(message, remove_directory, fstem)
                    os.remove(file_path)
                    return message, 404
                    
            return 'File saved successfully.', 200

@app.route('/api/enquire_upload_fail', methods = ['GET'])
def send_fail_log():

    session_id = request.headers.get('X-Session-ID')
    remove_directory = os.path.join(app_dir, 'user_upload', session_id, 'remove')
    zip_fname = 'error_report.zip'
    zip_path = os.path.join(remove_directory, zip_fname)
    if os.path.isfile(zip_path):
            os.remove(zip_path)
    arv = zipfile.ZipFile(zip_path, 'a')
    for fname in os.listdir(remove_directory):
        if os.path.splitext(fname)[1] == '.error':
            arv.write(os.path.join(remove_directory,fname), arcname=fname)
    arv.close()
    response = make_response(send_file(f'{base_dir}/{remove_directory}/{zip_fname}', 
                            as_attachment=True,
                            download_name=zip_fname))
    response.headers['Content-Type'] = 'application/zip'
    return response

@app.route('/api/upload_fa', methods=['POST'])
def upload_fasta():

    session_id = request.headers.get('X-Session-ID')

    for fname in request.files: ## only get one file
        # print(fname)
        file = request.files.get(fname)
        if file:
            user_directory = os.path.join(app_dir, 'user_upload', session_id)
            os.makedirs(user_directory, exist_ok=True)

            filename = 'user.fa'
            file_path = os.path.join(user_directory,filename)

            if os.path.islink(file_path) or os.path.isfile(file_path):
                os.remove(file_path)

            file.save(file_path)
            status, reason = is_valid_fasta(file_path)
            if status:
                return 'File saved successfully.', 200
            else:
                return 'File error: '+reason, 406
        else:
            return 'Upload unsuccessful', 404

@app.route('/api/spid_check', methods = ['POST'])
def check_id():

    spid = request.form.get('spid')
    session_id = request.headers.get('X-Session-ID')

    if int(spid) in known_species_ids:
        user_directory = os.path.join(app_dir, 'user_upload', session_id)
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

@app.route('/api/download_sc', methods=['GET']) 
def download_example():
    return send_file('rsc/human_example.sc', as_attachment=True)

@app.route('/api/download_fasta', methods=['GET']) 
def download_fasta_example():
    return send_file('rsc/fasta/9606.protein.sequences.v11.5.fa', as_attachment=True)

@app.route('/api/submit', methods=['POST'])
def handle_compute():
    session_id = request.headers.get('X-Session-ID')
    submit_type = request.get_json().get('submit_type')
    print(submit_type)
    print(session_id)
    user_directory = os.path.join(app_dir, 'user_upload', session_id)
    os.makedirs(user_directory+'/out', exist_ok=True)
    os.makedirs(user_directory+'/status', exist_ok=True)
    os.makedirs(user_directory+'/error', exist_ok=True)
    
    clean_up_computed(session_id)
    
    with open(user_directory+'/status/submit_type.txt', 'w') as wf:
        print(submit_type, file = wf)

    if submit_type == 'single':
        fname = os.listdir(f'{user_directory}/in')[0]
        fname_out, p = compute(user_directory, fname)
        if p.returncode == 0:
            return send_file(f'{base_dir}/{user_directory}/out/{fname_out}', as_attachment=True)
        else:
            fname_err = f'{os.path.splitext(fname_out)[0]}.error'
            abort(400, description = send_file(f'{base_dir}/{user_directory}/error/{fname_err}', as_attachment=True))
    else:
        zip_fname = 'results.zip'
        zip_path = os.path.join(user_directory, 'out', zip_fname)
        if os.path.isfile(zip_path):
            os.remove(zip_path)
        for fname in os.listdir(f'{user_directory}/in'):
            ## upload already failed, then no need to compute. 
            fname_err = f'{os.path.splitext(fname)[0]}.error' 
            
            # if os.path.isfile(f'{user_directory}/error/{fname_err}'):
            #     with open(f'{user_directory}/error/{fname_err}') as f:
            #         print(f.readline())

            arv = zipfile.ZipFile(zip_path, 'a')
            # if not os.path.isfile(f'{user_directory}/error/{fname_err}'):
            fname_out, p = compute(user_directory, fname)

            # print(fname_out)
            ## concatenate status files for sse to check
            status_dir = os.path.join(app_dir, 'user_upload', session_id, 'status')
            with open(os.path.join(status_dir, 'status.all'), 'w') as outfile:
                for i in os.listdir(status_dir):
                    if os.path.splitext(i)[1]=='.status':
                        print(i, file = outfile)
                    
            if len([l for l in open(f'{user_directory}/out/{fname_out}')]) > 0:
                arv.write(f'{user_directory}/out/{fname_out}', arcname=f'processed/{fname_out}')
            
            if os.path.isfile(f'{user_directory}/error/{fname_err}') and \
                len([l for l in open(f'{user_directory}/error/{fname_err}')]) > 0:
                arv.write(f'{user_directory}/error/{fname_err}', arcname=f'error/{fname_err}')
            arv.close()
            
        # import random, string
        # letters = string.ascii_lowercase
        # result_str = ''.join(random.choice(letters) for i in range(6))
        response = make_response(send_file(f'{base_dir}/{user_directory}/out/{zip_fname}', 
                        as_attachment=True,
                        download_name=zip_fname))
        response.headers['Content-Type'] = 'application/zip'
        return response
        
def compute(user_directory, fname):
    fname_out = os.path.splitext(fname)[0]+'.abu'
    fname_err = f'{os.path.splitext(fname_out)[0]}.error'
    p = sbp.run(f"python3 {app_dir}/scripts/ComputeAbundanceswithSC.py \
                -s {user_directory}/in/{fname} -f {user_directory}/user.fa \
                > {user_directory}/out/{fname_out}", 
                shell=True, capture_output=True)
    if p.stderr:
        
        with open(f'{user_directory}/error/{fname_err}','ab') as wf:
            wf.write(p.stderr)
    return fname_out, p

@app.route('/api/get_summary', methods = ['GET'])
def get_summary():
    session_id = request.headers.get('X-Session-ID')
    user_directory = os.path.join(app_dir, 'user_upload', session_id)
    print("getting multiple files' summary!")
    fname_info = []
    sucessfname = []
    for fname in os.listdir(f'{user_directory}/out'):
        if not fname.endswith('abu'):
            continue
        abus = []
        ps = []
        with open(f'{user_directory}/out/{fname}') as f:
            for l in f:
                try:
                    p, abu = l.split('\t')[:2]
                    ps.append(p)
                    abus.append(float(abu))
                except ValueError:
                    print(l)
        nprot = len(ps)
        min_abu = min(abus)
        max_abu = max(abus)
        mean_abu = sum(abus)/nprot
        tops = []
        for i in range(3):
            top = max(abus)
            top_idx = abus.index(top)
            abus.pop(top_idx)
            tops.append(ps.pop(top_idx))
                
        fname_info.append({
            'fname':os.path.splitext(fname)[0],
            'status':'success',
            'nprot':nprot,
            'top3': '\n'.join(tops),
            'info':f'Min:{min_abu:.3f}, Mean:{mean_abu:.0f}, Max:{max_abu:.0f}',
        })
        sucessfname.append(os.path.splitext(fname)[0])

    # check if all uploaded files have been covered
    missed = []
    for fname in os.listdir(f'{user_directory}/in'):
        fstem = os.path.splitext(fname)[0]
        if fstem not in sucessfname:
            missed.append(fstem)

    # check error directory (created at upload stage)
    if len(missed)>0 and os.path.isdir(f'{user_directory}/error'):
        
        for fname in os.listdir(f'{user_directory}/error'):
            fstem = os.path.splitext(fname)[0]
            if fstem in missed:
                with open(os.path.join(f'{user_directory}/error', fname)) as f:
                    err_info = f.readline().strip()

                fname_info.append({
                    'fname':fstem,
                    'status':'fail',
                    'nprot':0,
                    'top3':'',
                    'info':err_info,
                })
                missed.remove(fstem)

    ## still unknown reason
    for fstem in missed:
        fname_info.append({
                'fname':fstem,
                'status':'fail',
                'nprot':0,
                'top3':'',
                'info':'Unknown',
            })
    fname_info.sort(key=lambda x: x['fname'])
    return jsonify(fname_info)

@app.route('/api/get_topprotein', methods=['GET'])
def get_topprotein():
    session_id = request.headers.get('X-Session-ID')
    user_directory = os.path.join(app_dir, 'user_upload', session_id)
    os.makedirs(user_directory+'/out', exist_ok=True)

    print('handling top proteins!')
    for fname in os.listdir(f'{user_directory}/out'):
        if not fname.endswith('abu'):
            continue
        ps = []
        abus = []
        # print(f'{user_directory}/out/{fname}')
        with open(f'{user_directory}/out/{fname}') as f:
            for l in f:
                try:
                    p, abu = l.split('\t')[:2]
                    ps.append(p)
                    abus.append(float(abu))
                except ValueError:
                    print(l)
        top = sorted(zip(ps,abus), key = lambda x: x[1], reverse = True)[:20]
        top_data = [{'name': i, 'abu': round(j)} for (i,j) in top]

        return jsonify(top_data)

@app.route('/api/get_svg', methods=['GET'])
def get_svg():
    session_id = request.headers.get('X-Session-ID')
    user_directory = os.path.join(app_dir, 'user_upload', session_id)
    os.makedirs(user_directory+'/out', exist_ok=True)

    print('handling plot!')
    print(user_directory)
    for fname in os.listdir(f'{user_directory}/out'):
        if not fname.endswith('abu'):
            continue
        ps = []
        abus = []
        
        with open(f'{user_directory}/out/{fname}') as f:
            for l in f:
                try:
                    p, abu = l.split('\t')[:2]
                    ps.append(p)
                    abus.append(float(abu))
                except ValueError:
                    print(l) ## error log
                    
        sns.set(font_scale=1.2, style = 'white')
        plt.figure()
        ax=sns.histplot(x=abus, log_scale=True, color='darkgrey', linewidth=1, fill=False)
        ax.set(xlabel='protein abundance(ppm)', ylabel = '')
        sns.despine()
        def custom_formatter(x, pos):
            if x < 1:
                return f"{x:.1g}"  # Formats the number with one significant figure
            else:
                return f"{x:.0f}"  # Formats the number with no decimal places
        ax.xaxis.set_major_formatter(FuncFormatter(custom_formatter))
        ax.xaxis.set_major_locator(LogLocator(base=10, numticks=5)) # 5 ticks on the axis

        plt.title(f'{len(abus)} proteins', y=1.05) 
        plt.tight_layout()

        svg_fpath = os.path.join(user_directory, 'out', os.path.splitext(fname)[0]+'.svg')
        plt.savefig(svg_fpath)

        return send_file(os.path.join(base_dir,user_directory,'out', os.path.splitext(fname)[0]+'.svg'), mimetype='image/svg+xml')
        

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=os.getenv('PORT'), debug=True)
 

