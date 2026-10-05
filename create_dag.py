#!/usr/bin/env python3
"""
Generate a publication-quality DAG figure for the CirRealign pipeline.
Requires: graphviz (Python package) + dot (system binary)
"""

import graphviz

dot = graphviz.Digraph(
    "CirRealign_DAG",
    format="png",
    graph_attr={
        "rankdir": "TB",
        "fontname": "Helvetica",
        "fontsize": "14",
        "label": "CirRealign v1.2 — Pipeline DAG\nHPV16 Circular Genome Realignment",
        "labelloc": "t",
        "labeljust": "c",
        "bgcolor": "white",
        "dpi": "200",
        "pad": "0.5",
        "nodesep": "0.6",
        "ranksep": "0.8",
    },
)

# --- Style definitions ---
input_style = {
    "shape": "folder",
    "style": "filled",
    "fillcolor": "#E8F5E9",
    "color": "#388E3C",
    "fontname": "Helvetica",
    "fontsize": "11",
}
process_style = {
    "shape": "box",
    "style": "filled,rounded",
    "fillcolor": "#E3F2FD",
    "color": "#1565C0",
    "fontname": "Helvetica-Bold",
    "fontsize": "11",
    "penwidth": "2",
}
process_gap_style = {
    "shape": "box",
    "style": "filled,rounded",
    "fillcolor": "#FFF3E0",
    "color": "#E65100",
    "fontname": "Helvetica-Bold",
    "fontsize": "11",
    "penwidth": "2",
}
merge_style = {
    "shape": "box",
    "style": "filled,rounded",
    "fillcolor": "#F3E5F5",
    "color": "#6A1B9A",
    "fontname": "Helvetica-Bold",
    "fontsize": "11",
    "penwidth": "2",
}
summary_style = {
    "shape": "note",
    "style": "filled",
    "fillcolor": "#FFF9C4",
    "color": "#F9A825",
    "fontname": "Helvetica",
    "fontsize": "10",
}
output_style = {
    "shape": "folder",
    "style": "filled",
    "fillcolor": "#FFEBEE",
    "color": "#C62828",
    "fontname": "Helvetica",
    "fontsize": "11",
}

edge_nogap = {"color": "#1565C0", "penwidth": "2"}
edge_gap = {"color": "#E65100", "penwidth": "2", "style": "dashed"}
edge_merge = {"color": "#6A1B9A", "penwidth": "2"}
edge_summary = {"color": "#9E9E9E", "style": "dotted", "penwidth": "1.5"}

# --- Input ---
dot.node("input_csv", "pass_samples.txt\n(sample, lineage, BAM)", **input_style)
dot.node(
    "ref_elong",
    "Reference genomes\n(elongated: {lineage}_{elong}.fasta)",
    **input_style,
)
dot.node(
    "ref_regular",
    "Reference genomes\n(regular: {lineage}.fasta)",
    **input_style,
)

# --- Processes (no-gap path) ---
dot.node(
    "bwa_aln",
    "bwa_aln\n─────────────────────\nBWA-aln → elongated ref\nSplit: no-gap / gap reads",
    **process_style,
)
dot.node(
    "abra",
    "abra\n─────────────────────\nABRA2 realignment\n(elongated ref)",
    **process_style,
)
dot.node(
    "realignsamfile",
    "realignsamfile\n─────────────────────\nCircularMapper realign\n(elongated → linear coords)",
    **process_style,
)

# --- Processes (gap path) ---
dot.node(
    "bwa_mem",
    "bwa_mem_wo_elongation\n─────────────────────\nBWA-mem → regular ref\n(gap-containing reads)",
    **process_gap_style,
)
dot.node(
    "abra_wo",
    "abra_wo_elongation\n─────────────────────\nABRA2 realignment\n(regular ref)",
    **process_gap_style,
)

# --- Merge ---
dot.node(
    "merge",
    "merge_aligned_reads\n─────────────────────\nsamtools merge\n(no-gap + gap BAMs)",
    **merge_style,
)

# --- Summary processes ---
dot.node("sum_bwa", "summaryAlignment_Bwa\n(no-gap BWA stats)", **summary_style)
dot.node("sum_bwa_gap", "summaryAlignment_Bwa_gap\n(all-reads BWA stats)", **summary_style)
dot.node("sum_cir", "summaryAlignment_Cir\n(CircularMapper stats)", **summary_style)
dot.node("sum_merge", "summaryAlignment_merge\n(final merged stats)", **summary_style)

# --- Output ---
dot.node("final_bam", "Final merged BAM\n(*.merged.bam)", **output_style)
dot.node("summary_out", "Summary tables\n(summary_realign_*.out)", **output_style)

# --- Edges: Input → bwa_aln ---
dot.edge("input_csv", "bwa_aln", label="  filtered_bam  ", **edge_nogap)
dot.edge("ref_elong", "bwa_aln", label="  ref + BED  ", **edge_nogap)

# --- No-gap path ---
dot.edge("bwa_aln", "abra", label="  bwa_out\n  (no-gap reads)  ", **edge_nogap)
dot.edge("ref_elong", "abra", style="dotted", color="#1565C0")
dot.edge("abra", "realignsamfile", label="  arba_bam  ", **edge_nogap)
dot.edge("ref_elong", "realignsamfile", style="dotted", color="#1565C0")
dot.edge("realignsamfile", "merge", label="  realign_bam  ", **edge_merge)

# --- Gap path ---
dot.edge("bwa_aln", "bwa_mem", label="  gap_bam\n  (gap reads)  ", **edge_gap)
dot.edge("ref_regular", "bwa_mem", label="  ref + BED  ", **edge_gap)
dot.edge("bwa_mem", "abra_wo", label="  bwa_gap_out  ", **edge_gap)
dot.edge("ref_regular", "abra_wo", style="dotted", color="#E65100")
dot.edge("abra_wo", "merge", label="  arba_gap_bam  ", **edge_merge)

# --- Merge → Output ---
dot.edge("merge", "final_bam", label="  merged BAM  ", **edge_merge)

# --- Summary edges ---
dot.edge("bwa_aln", "sum_bwa", label="  bwa_flag  ", **edge_summary)
dot.edge("bwa_aln", "sum_bwa_gap", label="  bwa_gap_flag  ", **edge_summary)
dot.edge("realignsamfile", "sum_cir", label="  realign_flag  ", **edge_summary)
dot.edge("merge", "sum_merge", label="  merge_bam_flag  ", **edge_summary)

dot.edge("sum_bwa", "summary_out", **edge_summary)
dot.edge("sum_bwa_gap", "summary_out", **edge_summary)
dot.edge("sum_cir", "summary_out", **edge_summary)
dot.edge("sum_merge", "summary_out", **edge_summary)

# --- Legend (as a subgraph) ---
with dot.subgraph(name="cluster_legend") as legend:
    legend.attr(
        label="Legend",
        style="dashed",
        color="gray",
        fontname="Helvetica-Bold",
        fontsize="12",
    )
    legend.node(
        "leg1",
        "No-gap read path\n(BWA-aln → CircularMapper)",
        shape="box",
        style="filled,rounded",
        fillcolor="#E3F2FD",
        color="#1565C0",
        fontsize="9",
        fontname="Helvetica",
    )
    legend.node(
        "leg2",
        "Gap read path\n(BWA-mem → ABRA2)",
        shape="box",
        style="filled,rounded",
        fillcolor="#FFF3E0",
        color="#E65100",
        fontsize="9",
        fontname="Helvetica",
    )
    legend.node(
        "leg3",
        "Merge step",
        shape="box",
        style="filled,rounded",
        fillcolor="#F3E5F5",
        color="#6A1B9A",
        fontsize="9",
        fontname="Helvetica",
    )
    legend.node(
        "leg4",
        "Summary / QC",
        shape="note",
        style="filled",
        fillcolor="#FFF9C4",
        color="#F9A825",
        fontsize="9",
        fontname="Helvetica",
    )
    legend.edge("leg1", "leg2", style="invis")
    legend.edge("leg2", "leg3", style="invis")
    legend.edge("leg3", "leg4", style="invis")


# Render
output_path = "/tmp/CirRealign/dag"
dot.render(output_path, cleanup=True)
print(f"DAG saved to {output_path}.png")
