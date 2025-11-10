import azure.functions as func
import azure.cognitiveservices.speech as speechsdk
import time
import json
import os

# 1. Carregue as chaves das Configurações de Aplicativo
SPEECH_KEY = os.environ.get('SPEECH_KEY')
SPEECH_REGION = os.environ.get('SPEECH_REGION')

# 2. Configure e inicialize o sintetizador FORA do handler para reuso "warm"
try:
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_synthesis_voice_name = 'pt-BR-FranciscaNeural' # Voz Neural pt-BR
    
    # Configura a saída de áudio para "null" (stream em memória, sem arquivo/speaker)
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=False, filename=None)
    
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )
except Exception as e:
    speech_synthesizer = None
    print(f"Erro CRÍTICO ao inicializar o SpeechSynthesizer: {str(e)}")


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handler da Azure Function para testar o Speech Service.
    Recebe o texto, chama a API e retorna o tempo.
    """
    if not speech_synthesizer:
        return func.HttpResponse("Erro critico: Sintetizador de fala nao inicializado.", status_code=500)
        
    # 1. Registra o início do código da função
    function_code_start_time = time.perf_counter()

    try:
        # 2. Obtém o texto do corpo da requisição
        req_body = req.get_json()
        if not req_body or 'text' not in req_body:
            return func.HttpResponse('"text" nao encontrado no JSON.', status_code=400)
        
        text_to_synthesize = req_body.get('text')
            
    except ValueError:
        return func.HttpResponse('Corpo da requisicao JSON invalido.', status_code=400)

    # 3. Registra o início da chamada específica à API
    api_call_start = time.perf_counter()
    
    try:
        # 4. Executa a chamada para o Azure Speech (espera a conclusão com .get())
        speech_synthesis_result = speech_synthesizer.speak_text_async(text_to_synthesize).get()

        api_call_duration_ms = (time.perf_counter() - api_call_start) * 1000
        
        # 5. Verifica se a síntese teve sucesso
        if speech_synthesis_result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            return func.HttpResponse(f"Erro na sintese: {speech_synthesis_result.reason}", status_code=500)

        # 6. Calcula o tempo total do código da função
        function_code_duration_ms = (time.perf_counter() - function_code_start_time) * 1000

        # 7. Retorna as métricas (o áudio não é retornado, só processado)
        response_data = {
            'message': 'Audio gerado com sucesso.',
            'metrics_internal': {
                'api_call_duration_ms': round(api_call_duration_ms, 2),
                'function_code_duration_ms': round(function_code_duration_ms, 2)
            }
        }
        return func.HttpResponse(
            body=json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(f'Erro na API do Azure Speech: {str(e)}', status_code=500)

