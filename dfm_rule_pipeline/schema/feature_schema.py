from.features import features_dict

def load_feature_schema() -> str:
    """
    Returns the full feature schema as a single text block
    for grounding the LLM.
    """
    blocks = []
    for domain, text in features_dict.items():
        blocks.append(f"### {domain}\n{text.strip()}")
    return "\n\n".join(blocks)
