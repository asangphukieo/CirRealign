# CirRealign

A Nextflow pipeline for realigning HPV16 sequencing reads to sub-lineage-specific reference genomes using a circular genome mapping strategy.

## Overview

HPV16 has a circular genome (~7.9 kb), which creates alignment artifacts at the origin of replication when using standard linear-reference aligners. **CirRealign** addresses this by:

1. **Elongating** the reference genome by appending the first *N* bases to the end, creating a linear representation that spans the circular junction
2. **Splitting reads** into gap-free and gap-containing categories after initial alignment
3. **Routing reads** through optimized alignment paths:
   - **No-gap reads** → BWA-aln (elongated ref) → ABRA2 → CircularMapper realignment
   - **Gap-containing reads** → BWA-mem (non-elongated ref) → ABRA2
4. **Merging** both read sets into a final BAM file with accurate coordinates

### Pipeline Workflow

```
Input BAM ──► bwa_aln (elongated ref)
                │
                ├── no-gap reads ──► abra2 (elongated ref) ──► realignsamfile ──┐
                │                                                                ├──► merge ──► Final BAM
                └── gap reads ──► bwa_mem (non-elongated ref) ──► abra2 ────────┘
```

### Version History

- **v1.2** (current): Replaced BWA-aln with BWA-mem for gap-containing read pipeline (yields more mapped reads); kept BWA-aln for no-gap read pipeline (yields more no-gap reads)
- **v1.1**: Added alignment with sub-lineage genome without elongation factor; merge all aligned reads from both pipelines

## Requirements

### Software

- [Nextflow](https://www.nextflow.io/) (version 22.10.x, DSL1)
- [BWA](http://bio-bwa.sourceforge.net/) (bwa aln + bwa mem)
- [SAMtools](http://www.htslib.org/)
- [ABRA2](https://github.com/mozack/abra2)
- [CircularMapper](https://circularmapper.readthedocs.io/) (provides `realignsamfile`)

### Reference Files

For each HPV16 sub-lineage (e.g., `A1`, `A2`, `A4`, `D2`), you need:

| File | Description |
|------|-------------|
| `{lineage}.fasta` | Sub-lineage reference genome |
| `{lineage}.fasta.bed` | Target regions BED file for ABRA2 |
| `{lineage}_{elongation}.fasta` | Elongated reference (genome + first N bases appended) |
| `{lineage}_{elongation}.fasta.bed` | Target regions BED for elongated reference |

All FASTA files must be BWA-indexed (`bwa index <ref.fasta>`).

## Installation

```bash
# Clone the repository
git clone https://github.com/asangphukieo/CirRealign.git
cd CirRealign

# Verify Nextflow is installed (requires Java 11+)
nextflow -version
```

## Usage

### Basic Run

```bash
nextflow run CirRealign.nf \
    --input_summary pass_samples.txt \
    --ref_sublineage_folder /path/to/ref_sublineage/ \
    --output_folder ./results \
    --elongation 400 \
    --cpu 4 \
    --mem 40
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--input_summary` | Yes | `./pass_samples.txt` | CSV file listing samples (see format below) |
| `--ref_sublineage_folder` | No | *(hardcoded)* | Path to folder containing sub-lineage reference genomes |
| `--output_folder` | No | `.` | Output directory |
| `--elongation` | No | `400` | Number of bases from genome start appended to end |
| `--cpu` | No | `2` | Number of CPUs per process |
| `--mem` | No | `40` | Memory in GB per process |
| `--help` | No | - | Show help message |

### Input File Format

The `--input_summary` file is a CSV with three columns (no header):

```
sample_name,sub_lineage,path_to_bam
```

Example (`pass_samples.txt`):
```
sample1,A1,/data/input_bam/sample1.bam
sample2,A2,/data/input_bam/sample2.bam
sample3,D2,/data/input_bam/sample3.bam
```

- **sample_name**: Sample identifier
- **sub_lineage**: Predicted HPV16 sub-lineage (e.g., A1, A2, A4, D2)
- **path_to_bam**: Absolute path to the input BAM file (must contain @RG header with ID and SM tags)

### Output

```
output_folder/
├── bwa_bam/                          # Initial BWA-aln aligned BAMs (no-gap reads)
├── bwa_bam_wo_elongation/            # BWA-mem aligned BAMs (gap reads, non-elongated ref)
├── abra_bam/                         # ABRA2 realigned BAMs (no-gap reads)
├── abra_bam_wo_elongation/           # ABRA2 realigned BAMs (gap reads)
├── realigned_bam/                    # CircularMapper realigned BAMs (no-gap reads)
├── final_realigned_bam/              # Final merged BAMs (gap + no-gap)
│   ├── sample1.merged.bam
│   ├── sample1.merged.bam.bai
│   └── ...
├── summary_realign_Bwa.out           # BWA-aln alignment stats (no-gap)
├── summary_realign_Bwa_gap.out       # BWA-aln alignment stats (all reads)
├── summary_realign_Cir.out           # CircularMapper realignment stats
└── summary_realign_all.out           # Final merged alignment stats
```

The primary output is `final_realigned_bam/*.merged.bam` — these are the final realigned BAM files suitable for downstream variant calling.

### Example: Full Workflow

```bash
# Step 1: Prepare sub-lineage references (example for A1 with elongation=400)
# The genome FASTA should already exist. Create the elongated version:
# cat A1.fasta | awk '/^>/{print; next}{seq=seq$0}END{print seq substr(seq,1,400)}' > A1_400.fasta
# bwa index A1.fasta
# bwa index A1_400.fasta
# Create BED files covering the full genome:
# echo -e "A1\t0\t7905" > A1.fasta.bed
# echo -e "A1\t0\t8305" > A1_400.fasta.bed

# Step 2: Prepare sample sheet
# (typically generated from QC pipeline output + filter_sample.R)
cat > pass_samples.txt << EOF
SAMPLE_001,A1,/data/bam/SAMPLE_001.bam
SAMPLE_002,A2,/data/bam/SAMPLE_002.bam
SAMPLE_003,A1,/data/bam/SAMPLE_003.bam
EOF

# Step 3: Run the pipeline
nextflow run CirRealign.nf \
    --input_summary pass_samples.txt \
    --ref_sublineage_folder /data/ref_sublineage/ \
    --output_folder ./01_CirRealign \
    --elongation 400 \
    --cpu 4 \
    --mem 40 \
    -resume

# Step 4: Check results
cat ./01_CirRealign/summary_realign_all.out
ls ./01_CirRealign/final_realigned_bam/
```

### Resume Failed Runs

Nextflow supports resuming from cached results:

```bash
nextflow run CirRealign.nf [same parameters] -resume
```

## Test Data

A mock test dataset is provided under `test_data/` for validating the pipeline setup:

```
test_data/
├── pass_samples.txt                  # Sample sheet (2 samples)
├── ref_sublineage/                   # Mock HPV16 sub-lineage references
│   ├── A1.fasta                      # Sub-lineage A1 (500 bp mock genome)
│   ├── A1.fasta.bed
│   ├── A1_50.fasta                   # Elongated A1 (550 bp)
│   ├── A1_50.fasta.bed
│   ├── A2.fasta                      # Sub-lineage A2
│   ├── A2.fasta.bed
│   ├── A2_50.fasta                   # Elongated A2
│   └── A2_50.fasta.bed
└── input_bam/                        # Mock paired-end BAM files
    ├── sample1.bam                   # 50 read pairs, lineage A1
    ├── sample1.bam.bai
    ├── sample2.bam                   # 50 read pairs, lineage A2
    └── sample2.bam.bai
```

To run with test data (requires bwa, samtools, abra2, and CircularMapper installed):

```bash
# First, index the test references
for ref in test_data/ref_sublineage/*.fasta; do
    bwa index "$ref"
done

# Update pass_samples.txt with absolute paths
BASEDIR=$(pwd)
sed -i "s|test_data|${BASEDIR}/test_data|g" test_data/pass_samples.txt

# Run pipeline with test data
nextflow run CirRealign.nf \
    --input_summary test_data/pass_samples.txt \
    --ref_sublineage_folder test_data/ref_sublineage/ \
    --elongation 50 \
    --output_folder ./test_output \
    --cpu 1 \
    --mem 2
```

The test data was generated using `generate_test_data.py` (requires Python 3 + pysam).

## Citation

If you use this pipeline, please cite:

- Nextflow: Di Tommaso, P., et al. *Nextflow enables reproducible computational workflows.* Nature Biotechnology 35, 316-319 (2017). doi:10.1038/nbt.3820
- BWA: Li, H. & Durbin, R. *Fast and accurate short read alignment with Burrows-Wheeler transform.* Bioinformatics 25, 1754-1760 (2009).
- ABRA2: Mose, L.E., et al. *ABRA2: improved assembly-based realignment.* Bioinformatics 35, 2966-2967 (2019).
- CircularMapper: Peltzer, A., et al. *CircularMapper: An efficient tool for reference-based mapping of circular genomes.* (2016).

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

Copyright (C) IARC/WHO
