import utils
from datetime import datetime
import ast


def process_request(exam_requested, indication):

    # get top n protocols
    n = 6
    topk_protocols, topk_definitions = utils.get_topk_definitions(indication,exam_requested,top_k=n)

    # get protocol prediction
    protocol_dict_defs = {k.strip():v.strip() for k,v in zip(topk_protocols,topk_definitions)}
    protocol_thinking, protocol_pred = utils.get_protocol(indication,exam_requested,protocol_dict_defs, max_tokens=1024, enable_thinking=True)


    #get priority prediction
    start_time = datetime.now()
    if not any(x in protocol_pred for x in ['Procedure','No appropriate protocol found']):
        thinking, priority_pred = utils.get_priority(indication, exam_requested, protocol_pred, max_tokens=1024,enable_thinking=True)
        if priority_pred == 'Not in guidelines':
            priority_thinking, priority_pred = utils.get_inferred_priority(indication, exam_requested, thinking, protocol_pred, max_tokens=1024,
                                                         enable_thinking=True)

    else:
        if 'Procedure' in protocol_pred:
            priority_thinking, priority_pred = '', 'Procedure Protocol'
        elif 'No appropriate protocol found':
            priority_thinking, priority_pred = '', 'No Protocol Found'
        else:
            priority_thinking, priority_pred = '', ''

    output = {'protocol_thinking': protocol_thinking, 'protocol_pred': protocol_pred,
              'priority_thinking': priority_thinking, 'priority_thinking': priority_pred}


    return output
