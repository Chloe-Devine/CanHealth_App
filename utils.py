import pandas as pd
print('loading llm')
import llm_setup_runpod as llm
print('llm loaded')
import torch
import ast

from sentence_transformers import SentenceTransformer


protocol_defs = pd.read_excel('data/definitions/Protocol Definitions v6.xlsx')
protocol_dfs = dict(zip(protocol_defs["Protocol"], protocol_defs["Definition 2"]))

protocol_2_guide = dict(zip(protocol_defs["Protocol"], protocol_defs["Prioritization Guide Section"]))


guide_sections_file = pd.read_excel('data/prioritization_guide/prioritization_guide_contents v5.xlsx')
guide_contents_dict = dict(zip(guide_sections_file["Guide Section Name"], guide_sections_file["Contents"]))

prompts = pd.read_excel('data/prompts/prompts v7.xlsx')
prompts_dict = dict(zip(prompts["Type"], prompts["prompt"]))

print('loading embedding model')
##Embedding Set Up
embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")#mixedbread-ai/mxbai-embed-large-v1 #"all-MiniLM-L6-v2"
print('embedding model loaded')
# Corpus with example documents
corpus = [k +': ' + v for k, v in protocol_dfs.items()]


corpus_embeddings = embedder.encode_document(corpus, convert_to_tensor=True)

def get_topk_definitions(indication, exam_requested, top_k=5):

    query = f"Exam Requested: {exam_requested}, Indication: {indication}"
    query_embedding = embedder.encode_query(query, convert_to_tensor=True)

    # We use cosine-similarity and torch.topk to find the highest 5 scores
    similarity_scores = embedder.similarity(query_embedding, corpus_embeddings)[0]
    scores, indices = torch.topk(similarity_scores, k=top_k)

    topk_protocol_defs = [corpus[idx] for idx in indices]

    # topk_protocols = [key for key, value in protocol_dfs.items() if value in topk_protocol_defs]
    topk_protocols = [text[:text.find(':')] for text in topk_protocol_defs]
    topk_protocol_defs = [text[text.find(':')+1:].strip() for text in topk_protocol_defs]


    return topk_protocols, topk_protocol_defs



def get_protocol(indication, exam_requested, protocol_definitions, api_key, max_tokens = 512, enable_thinking=False):
    protocol_prompt_txt = prompts_dict['Protocol'].format(indication = indication, exam_requested=exam_requested, definitions = protocol_definitions)
    thinking_content, answer = llm.llm_execute(protocol_prompt_txt, max_tokens=max_tokens,api_key=api_key, enable_thinking=enable_thinking)
    return thinking_content, answer

def get_guide_contents(protocol_pred):
    protocol_pred = ast.literal_eval(protocol_pred)
    guide_contents = guide_contents_dict['Introduction']
    section_names = []
    for pred in protocol_pred:
        if '(B)' in pred:
            pred = pred.replace('(B)', '').strip()
        section_names.append(protocol_2_guide[pred])
    section_names = ",".join(section_names)
    section_names = section_names.split(',')
    seen = set()
    for section in section_names:
        if section not in seen:
            content = "\n\n" + guide_contents_dict[section]
            guide_contents += content
    content = '\n\n' + guide_contents_dict['Additional Notes']
    guide_contents += content
    return guide_contents

def get_priority(indication, exam_requested, protocol_pred,api_key,max_tokens = 512, enable_thinking=False):
    guide_contents = get_guide_contents(protocol_pred)
    prompt = prompts_dict['Priority'].format(indication=indication, exam_requested=exam_requested, contents=guide_contents)
    thinking_content, answer= llm.llm_execute(prompt, max_tokens=max_tokens, api_key=api_key,enable_thinking=enable_thinking)
    return thinking_content, answer

def get_inferred_priority(indication, exam_requested, previous_reasoning,protocol_pred,api_key,max_tokens = 512, enable_thinking=False):
    guide_contents = get_guide_contents(protocol_pred)
    prompt = prompts_dict['Priority2'].format(indication=indication, exam_requested=exam_requested, contents=guide_contents)
    thinking_content, answer= llm.llm_execute(prompt, max_tokens=max_tokens,  api_key=api_key, enable_thinking=enable_thinking)
    return thinking_content, answer











