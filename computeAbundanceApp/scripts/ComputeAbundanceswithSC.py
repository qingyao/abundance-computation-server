### rewrite ComputeAbundanceswithSC.java
import argparse, os, sys, re
from collections import defaultdict

normalize = True
prefixSize = 6
minPepLength = 4

peptideLookup = defaultdict(set)
peptideCount = {}
id_seq = {}
allPepLengths = defaultdict(int)
peptide2protein = defaultdict(set)
protein2peptideRawCount = defaultdict(dict)
protein2peptideCount = defaultdict(dict)
observedPepLengths = defaultdict(int)
PepLengthFactor = {}

def main():
    global prefixSize
    global statusFile
    global errorFile
    parser = argparse.ArgumentParser()

    parser.add_argument('-f','--fasta',  type=str, help = 'fasta file', required = True)
    parser.add_argument('-s','--scfile', type=str, help = 'spectral counting file with peptide sequence and quantification', required = True)
    parser.add_argument('-p','--peptide', help = 'print protein - peptide - spectral count information', action="store_true")
    args = parser.parse_args()
    pepFile = args.scfile
    fastaFile = args.fasta
    pepChoice = args.peptide
    status_dir = os.path.join(os.path.split(pepFile)[0], os.pardir,'status')
    error_dir = os.path.join(os.path.split(pepFile)[0], os.pardir,'error')
    basename = os.path.basename(pepFile)
    statusFile = os.path.join(status_dir, os.path.splitext(basename)[0] + '.status')
    errorFile = os.path.join(error_dir, os.path.splitext(basename)[0] + '.error')

    newMinPepLength = readPeptides(pepFile)
    while newMinPepLength != 0:
        prefixSize = newMinPepLength
        newMinPepLength = readPeptides(pepFile)

    readFasta(fastaFile)
    mapPeptides()
    digestFasta()
    calcPepLengthFactor()

    protein_abu = {}
    protein_scount = {}
    total = 0
    for protein in protein2peptideCount:
        abu = calcProteinAbundance(protein)
        scount = rawspectralcount(protein)
        if abu == -1 or scount == -1:
            continue
        total += abu
        protein_abu[protein] = abu
        protein_scount[protein] = scount
    
    if pepChoice:
        if len(protein2peptideRawCount) == 0:
            sys.exit('No proteins found')
        for protein, pepSeq_count  in protein2peptideRawCount.items(): 
            for pepSeq, count in pepSeq_count.items():
                print(protein, pepSeq, count, sep = '\t', file = sys.stdout)
    else:
        if len(protein_abu) == 0:
            sys.exit('No proteins found')
        for protein, abu in protein_abu.items():
            print(protein, abu* 10**6 / total, protein_scount[protein], sep = '\t', file = sys.stdout)

def readPeptides(filepath):
    global peptideLookup
    global peptideCount
    with open(filepath) as f:
        line_count = 0
        for i, l in enumerate(f):
            try:
                seq, quant = l.split('\t')
            except ValueError:
                with open(errorFile, 'a') as wf:
                    print(os.path.basename(filepath), '\tline ', i, ': Abnormal line in spectral counting file, skip line...', sep = '', file=wf)
                continue
            try:
                quant = round(float(quant))
            except ValueError:
                with open(errorFile, 'a') as wf:
                    print(os.path.basename(filepath), '\tline ', i, ': Second column not a number', sep = '', file=sys.stderr)
                continue
            
            if len(seq) < minPepLength: ## ignore 
                continue
            elif len(seq) < prefixSize:
                with open(errorFile, 'a') as wf:
                    print('warning: lookup prefix longer than shortest peptide - resetting now to smaller value (',len(seq), ') and trying again', file=wf) 
                peptideCount = {}
                peptideLookup = defaultdict(set)
                return len(seq)
            
            if seq in peptideCount:
                with open(errorFile, 'a') as wf:
                    print('warning: sequence not unique, sum the quantity ...', file=wf)
                peptideCount[seq] += quant
            else:
                peptideCount[seq] = quant
            
            peptideLookup[seq[:prefixSize]].add(seq)
            line_count += 1
        # print('* no of peptides read from ' + os.path.basename(filepath) + ': ' + str(line_count), file=sys.stderr)
        
        return 0
    
def readFasta(fastaFile):
    global id_seq
    with open(fastaFile) as fr:
        for l in fr:
            if l.startswith('>'):
                string_id = l.strip().replace('>', '')

            else:
                if string_id in id_seq:
                    id_seq[string_id] += l.strip()
                else:
                    id_seq[string_id] = l.strip()
    # print('* no of protein sequences read from ' + fastaFile + ': ' + str(len(id_seq)), file=sys.stderr)
    
   
def digestFasta():
    global allPepLengths
    for seq in id_seq.values():
        for pep in re.split('R|K', seq):
            allPepLengths[len(pep)+1] += 1
    
            
def calcPepLengthFactor():
    global PepLengthFactor
    
    for l, cnt in observedPepLengths.items():
        PepLengthFactor[l] = cnt / allPepLengths[l]
    
    
def mapPeptides():
    total = len(id_seq)
    count = 0
    step = 0
    
    for proteinID, seq in id_seq.items():
        for i in range(len(seq)-prefixSize):
            prefix = seq[i:(prefixSize+i)]
            if prefix in peptideLookup:
                for pepSeq in peptideLookup[prefix]:
                    if seq[i:len(pepSeq)+i]== pepSeq:
                        peptide2protein[pepSeq].add(proteinID)
                
        count += 1
        if (round(count / total, 1) >= step):
            with open(statusFile,'w') as wf:
                print(f'{round(step*100)}%', file=wf)
            step += 0.1
            
    for pepSeq, proteins in peptide2protein.items():
        for protein in proteins:
            protein2peptideRawCount[protein][pepSeq] = peptideCount[pepSeq]
            protein2peptideCount[protein][pepSeq] = peptideCount[pepSeq]/len(proteins) ## normalize by number of matched proteins
            
        observedPepLengths[len(pepSeq)] += peptideCount[pepSeq] ## "observed peptide" count only ones that match to protein
        
  
def calcProteinAbundance(protein):
    if not protein in protein2peptideCount:
        return -1
    peptideCountNumerator = weighedAbundance = 0
    for pepSeq, pepCount in protein2peptideCount[protein].items():
        peptideCountNumerator += pepCount * len(pepSeq) 
    
    if peptideCountNumerator == 0 or not protein in id_seq:
        return -1
    
    adjustedLength = 0
    for pep in re.split('R|K', id_seq[protein]):
        l = len(pep) + 1
        if (l >= 7 and l <= 40 and l in PepLengthFactor):
            adjustedLength += l * PepLengthFactor[l]
    if adjustedLength == 0:
        return -1
    
    weighedAbundance = peptideCountNumerator / adjustedLength
    return weighedAbundance

def rawspectralcount(protein):
    if not protein in protein2peptideRawCount:
        return -1
    
    proteinRawcount = 0
    for rawCount in protein2peptideRawCount[protein].values():
        proteinRawcount += rawCount
        
    if proteinRawcount == 0:
        return -1
    
    return proteinRawcount

if __name__ == '__main__':
    main()