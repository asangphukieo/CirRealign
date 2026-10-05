#!/usr/bin/env python3
"""
Generate mock test data for CirRealign pipeline testing.

Creates:
  - Mock HPV16 sub-lineage reference genomes (regular + elongated)
  - BWA index files
  - BED target files
  - Mock paired-end BAM files
  - pass_samples.txt input file

The mock genome is a 500 bp circular sequence representing a simplified
HPV16 sub-lineage genome. The elongated version appends the first N bases
(elongation factor) to handle circular mapping at the origin.
"""

import os
import random
import pysam

random.seed(42)

# --- Configuration ---
GENOME_LEN = 500          # Mock genome length (bp)
ELONGATION = 50           # Elongation factor for circular reference
READ_LEN = 100            # Read length
NUM_PAIRS = 50            # Number of read pairs per sample
INSERT_SIZE = 200         # Mean insert size
SUBLINEAGES = ["A1", "A2"]
SAMPLES = {
    "sample1": "A1",
    "sample2": "A2",
}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
REF_DIR = os.path.join(OUTPUT_DIR, "ref_sublineage")
BAM_DIR = os.path.join(OUTPUT_DIR, "input_bam")

os.makedirs(REF_DIR, exist_ok=True)
os.makedirs(BAM_DIR, exist_ok=True)


def random_seq(length):
    return "".join(random.choice("ACGT") for _ in range(length))


def mutate_seq(seq, rate=0.02):
    """Introduce SNPs at the given rate."""
    bases = list(seq)
    for i in range(len(bases)):
        if random.random() < rate:
            bases[i] = random.choice([b for b in "ACGT" if b != bases[i]])
    return "".join(bases)


def write_fasta(path, name, seq):
    with open(path, "w") as f:
        f.write(f">{name}\n")
        for i in range(0, len(seq), 80):
            f.write(seq[i : i + 80] + "\n")


def write_bed(path, name, seq_len):
    with open(path, "w") as f:
        f.write(f"{name}\t0\t{seq_len}\n")


def reverse_complement(seq):
    comp = {"A": "T", "T": "A", "C": "G", "G": "C", "N": "N"}
    return "".join(comp.get(b, "N") for b in reversed(seq))


def simulate_reads(genome, num_pairs, read_len, insert_size):
    """Generate paired-end reads from a genome."""
    reads = []
    genome_len = len(genome)
    for i in range(num_pairs):
        # Random insert size with some variation
        ins = max(read_len + 10, int(random.gauss(insert_size, 30)))
        if ins > genome_len:
            ins = genome_len
        start = random.randint(0, genome_len - ins)
        fragment = genome[start : start + ins]
        r1_seq = fragment[:read_len]
        r2_seq = reverse_complement(fragment[-read_len:])
        r1_qual = "I" * read_len
        r2_qual = "I" * read_len
        reads.append(
            {
                "name": f"read_{i}",
                "r1_seq": r1_seq,
                "r2_seq": r2_seq,
                "r1_qual": r1_qual,
                "r2_qual": r2_qual,
                "pos": start,
                "ins": ins,
            }
        )
    return reads


def create_bam(bam_path, ref_name, ref_len, reads, read_len, sample_name):
    """Create a BAM file with paired-end alignments."""
    header = {
        "HD": {"VN": "1.6", "SO": "coordinate"},
        "SQ": [{"SN": ref_name, "LN": ref_len}],
        "RG": [{"ID": sample_name, "SM": sample_name, "PL": "ILLUMINA"}],
    }

    with pysam.AlignmentFile(bam_path, "wb", header=header) as outf:
        for r in reads:
            # Read 1 (forward)
            a1 = pysam.AlignedSegment()
            a1.query_name = r["name"]
            a1.query_sequence = r["r1_seq"]
            a1.flag = 99  # paired, proper pair, mate reverse strand, first in pair
            a1.reference_id = 0
            a1.reference_start = r["pos"]
            a1.mapping_quality = 60
            a1.cigar = [(0, read_len)]  # 100M
            a1.next_reference_id = 0
            a1.next_reference_start = r["pos"] + r["ins"] - read_len
            a1.template_length = r["ins"]
            a1.query_qualities = pysam.qualitystring_to_array(r["r1_qual"])
            a1.set_tag("RG", sample_name)

            # Read 2 (reverse)
            a2 = pysam.AlignedSegment()
            a2.query_name = r["name"]
            a2.query_sequence = r["r2_seq"]
            a2.flag = 147  # paired, proper pair, reverse strand, second in pair
            a2.reference_id = 0
            a2.reference_start = r["pos"] + r["ins"] - read_len
            a2.mapping_quality = 60
            a2.cigar = [(0, read_len)]  # 100M
            a2.next_reference_id = 0
            a2.next_reference_start = r["pos"]
            a2.template_length = -r["ins"]
            a2.query_qualities = pysam.qualitystring_to_array(r["r2_qual"])
            a2.set_tag("RG", sample_name)

            outf.write(a1)
            outf.write(a2)

    # Sort and index
    pysam.sort("-o", bam_path + ".tmp", bam_path)
    os.rename(bam_path + ".tmp", bam_path)
    pysam.index(bam_path)


def main():
    print("Generating mock test data for CirRealign pipeline...")

    # Generate a base HPV16 genome
    base_genome = random_seq(GENOME_LEN)

    # Create sub-lineage references
    genomes = {}
    for lineage in SUBLINEAGES:
        genome = mutate_seq(base_genome, rate=0.02)
        genomes[lineage] = genome

        # Regular reference (non-elongated)
        ref_name = lineage
        ref_path = os.path.join(REF_DIR, f"{lineage}.fasta")
        write_fasta(ref_path, ref_name, genome)
        write_bed(
            os.path.join(REF_DIR, f"{lineage}.fasta.bed"),
            ref_name,
            len(genome),
        )

        # Elongated reference (circular handling)
        elong_genome = genome + genome[:ELONGATION]
        elong_ref_name = lineage
        elong_ref_path = os.path.join(REF_DIR, f"{lineage}_{ELONGATION}.fasta")
        write_fasta(elong_ref_path, elong_ref_name, elong_genome)
        write_bed(
            os.path.join(REF_DIR, f"{lineage}_{ELONGATION}.fasta.bed"),
            elong_ref_name,
            len(elong_genome),
        )

        print(f"  Created reference for {lineage}: {len(genome)} bp (elongated: {len(elong_genome)} bp)")

    # Create mock BAM files and pass_samples.txt
    samples_lines = []
    for sample_name, lineage in SAMPLES.items():
        genome = genomes[lineage]
        elong_genome = genome + genome[:ELONGATION]
        ref_name = lineage

        reads = simulate_reads(elong_genome, NUM_PAIRS, READ_LEN, INSERT_SIZE)

        bam_path = os.path.join(BAM_DIR, f"{sample_name}.bam")
        create_bam(
            bam_path,
            ref_name,
            len(elong_genome),
            reads,
            READ_LEN,
            sample_name,
        )

        samples_lines.append(f"{sample_name},{lineage},{bam_path}")
        print(f"  Created BAM for {sample_name} (lineage {lineage}): {NUM_PAIRS} read pairs")

    # Write pass_samples.txt
    samples_path = os.path.join(OUTPUT_DIR, "pass_samples.txt")
    with open(samples_path, "w") as f:
        for line in samples_lines:
            f.write(line + "\n")

    print(f"\nTest data written to: {OUTPUT_DIR}")
    print(f"Sample sheet: {samples_path}")
    print(f"References: {REF_DIR}")
    print(f"BAM files: {BAM_DIR}")
    print("\nTo run the pipeline with test data:")
    print(f"  nextflow run CirRealign.nf \\")
    print(f"    --input_summary {samples_path} \\")
    print(f"    --ref_sublineage_folder {REF_DIR}/ \\")
    print(f"    --elongation {ELONGATION} \\")
    print(f"    --output_folder ./test_output")


if __name__ == "__main__":
    main()
