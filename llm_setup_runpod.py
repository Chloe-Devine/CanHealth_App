import requests
import json
import time

nonthinking_settings = {
    'max_tokens': 2048,
    'temperature':0.7,
    'top_k':20,
    'top_p':0.8,
    'min_p': 0.01,
    'repetition_penalty' :1.05
}

thinking_settings = {
    'max_tokens': 2048,
    'temperature':0.6,
    'top_k':20,
    'top_p':0.95,
    'min_p': 0.01,
    'repetition_penalty' :1.05
}


# promptheader = "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n<|im_start|>user\n"
# promptfooter = "<|im_end|>\n<|im_start|>assistant\n"

promptheader = '''<|im_start|>user\n'''
promptfooter = '''\n<|im_end|>\n<|im_start|>assistant\n<think>'''


def llm_execute(prompt, max_tokens, api_key=None, settings=nonthinking_settings, enable_thinking=False, poll_interval=2):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    prompt = promptheader + prompt + promptfooter
    if not enable_thinking:
        prompt += "\n\n</think>\n\n"


    url = 'https://api.runpod.ai/v2/cwo0kpjuyp56xk/runsync'
    data = {
        "input": {
            "prompt": prompt,
            "sampling_params": {
                "temperature": settings['temperature'],
                "max_tokens": settings['max_tokens'],
                "top_p": settings['top_p'],
                "top_k":settings['top_k'],
                "repetition_penalty": settings['repetition_penalty']
            }
        }
    }
    response = requests.post(url, headers=headers, json=data, timeout=300)
    if response.status_code != 200:
        raise RuntimeError(f"RunPod returned {response.status_code}: {response.text}")

    resp_json = response.json()

    # Check if job is in queue and poll until it's completed
    while resp_json.get("status") in ["IN_QUEUE", "IN_PROGRESS"]:
        job_id = resp_json["id"]
        time.sleep(poll_interval)
        status_url = f"https://api.runpod.ai/v2/cwo0kpjuyp56xk/status/{job_id}"
        status_resp = requests.get(status_url, headers=headers)
        if status_resp.status_code != 200:
            raise RuntimeError(f"Status check failed: {status_resp.text}")
        resp_json = status_resp.json()
        if resp_json.get("status") == "FAILED":
            raise RuntimeError(f"RunPod job {job_id} failed: {resp_json}")

    # Now the job should be completed, extract output safely
    try:
        output_text = resp_json["output"][0]["choices"][0]["tokens"]
        if len(output_text) == 1:
            output = output_text[0]
            try:
                thinking_content = output[:output.find('</think>')]
                answer = output[output.find('</think>')+8:]
                return thinking_content, answer
            except:
                return output.strip(), 200
        else:
            output_list = []
            for reply in output_text:
                output_list.append(reply.strip())
            return output_list, 200
    except (KeyError, IndexError):
        output_text = str(resp_json)
        return output_text.strip(), 200

warmup_settings = {
    'max_tokens': 256,
    'temperature':0.6,
    'top_k':20,
    'top_p':0.95,
    'min_p': 0.01,
    'repetition_penalty' :1.05
}

def warmup_model(api_key=None):
    response= llm_execute(prompt='Hello', api_key=api_key, settings=warmup_settings)
    print('warmup done')


def llm_response(history, api_key=None, settings=nonthinking_settings, poll_interval=2):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        url = 'https://api.runpod.ai/v2/cwo0kpjuyp56xk/runsync'
        data = {
            "input": {
                "messages": history,
                "sampling_params": {
                    "temperature": settings['temperature'],
                    "max_tokens": settings['max_tokens'],
                    "top_p": settings['top_p'],
                    "top_k": settings['top_k'],
                    "repetition_penalty": settings['repetition_penalty'],
                }
            }
        }
        response = requests.post(url, headers=headers, json=data, timeout=900)
        if response.status_code != 200:
            raise RuntimeError(f"RunPod returned {response.status_code}: {response.text}")

        resp_json = response.json()

        # Check if job is in queue and poll until it's completed
        while resp_json.get("status") in ["IN_QUEUE", "IN_PROGRESS"]:
            job_id = resp_json["id"]
            time.sleep(poll_interval)
            status_url = f"https://api.runpod.ai/v2/cwo0kpjuyp56xk/status/{job_id}"
            status_resp = requests.get(status_url, headers=headers)
            if status_resp.status_code != 200:
                raise RuntimeError(f"Status check failed: {status_resp.text}")
            resp_json = status_resp.json()
            if resp_json.get("status") == "FAILED":
                raise RuntimeError(f"RunPod job {job_id} failed: {resp_json}")

        # Now the job should be completed, extract output safely
        try:
            output_text = resp_json["output"][0]["choices"][0]["tokens"]
            if len(output_text) == 1:
                output = output_text[0]
                return output.strip()
            else:
                output_list = []
                for reply in output_text:
                    output_list.append(reply.strip())
                return output_list
        except (KeyError, IndexError):
            output_text = str(resp_json)
            return output_text.strip()

