import os
import uuid
import json
import boto3
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar cliente de DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'no_data_table')
api_key = os.environ.get("API_KEY", "NOVALUE")

def handler(event, context):
    try:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
        }

        http_method = event['httpMethod']

        if http_method == 'GET':
            return handle_get(event, headers)
        elif http_method == 'POST':
            return handle_post(event, headers)
        else:
            return {
                'statusCode': 405,
                'headers': headers,
                'body': json.dumps({'message': 'Método no permitido'})
            }

    except json.JSONDecodeError as e:
        logger.error(f"Error al procesar el JSON: {str(e)}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': 'Error al procesar el JSON', 'error': str(e)})
        }
    except Exception as e:
        logger.error(f"Error interno del servidor: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Error interno del servidor', 'error': str(e)})
        }

def handle_get(event, headers):
    try:
        song = event["queryStringParameters"]["song"]
        songs = search_youtube(song)

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': "Se obtuvieron las canciones correctamente", "songs": songs})
        }
    except KeyError as e:
        logger.error(f"Falta el parámetro de consulta: {str(e)}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': 'Falta el parámetro de consulta', 'error': str(e)})
        }

def handle_post(event, headers):
    try:
        body = json.loads(event['body'])

        if 'action' not in body:
            raise ValueError("Falta el campo 'action' en el body")

        action = body['action']
        if action == 'add_queue':
            return put_item_dynamodb(body, headers)
        elif action == 'get_queue':
            return get_all_song_pending(headers)
        elif action == 'update_queue':
            return update_item_dynamodb(body, headers)
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'message': 'Acción no soportada'})
            }

    except ValueError as e:
        logger.error(f"Error en el body: {str(e)}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': 'Error en el body', 'error': str(e)})
        }

def put_item_dynamodb(body, headers):
    try:
        table = dynamodb.Table(table_name)

        item = body['item']
        item["song-id"] = str(uuid.uuid4())

        table.put_item(Item=item)
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'Item escrito correctamente'})
        }
    except Exception as e:
        logger.error(f"Error al escribir en DynamoDB: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Error al escribir en DynamoDB', 'error': str(e)})
        }

def update_item_dynamodb(body, headers):
    try:
        table = dynamodb.Table(table_name)
        item = body['item']
        
        key = {'song-id': item['song-id']}
        
        update_expression = "SET #s = :status"
        expression_attribute_values = {
            ':status': item['status']
        }
        expression_attribute_names = {
            '#s': 'status'
        }

        table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names
        )
        
        logger.info("Item actualizado en DynamoDB")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'Item actualizado correctamente'})
        }
    except Exception as e:
        logger.error(f"Error al actualizar en DynamoDB: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Error al actualizar en DynamoDB', 'error': str(e)})
        }

    
def get_all_song_pending(headers):
    try:
        table = dynamodb.Table(table_name)
        response = table.query(
            IndexName='status-index',
            KeyConditionExpression=Key('status').eq('pending')
        )

        items = response.get('Items', [])
        logger.info("Items obtenidos de DynamoDB con estado 'pending'")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'Items obtenidos correctamente', 'items': items})
        }
    except Exception as e:
        logger.error(f"Error al obtener ítems de DynamoDB: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Error al obtener ítems de DynamoDB', 'error': str(e)})
        }

def search_youtube(query):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)

        request = youtube.search().list(
            q=query,
            part='snippet',
            maxResults=5,
            type='video'
        )
        response = request.execute()

        results = []
        for item in response['items']:
            title = item['snippet']['title']
            video_id = item['id']['videoId']
            thumbnail_url = item['snippet']['thumbnails']['default']['url']
            results.append({'title': title, 'videoId': video_id, 'thumbnail_url': thumbnail_url})

        return results
    except HttpError as e:
        logger.error(f"Error en la API de YouTube: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error al buscar en YouTube: {str(e)}")
        raise
