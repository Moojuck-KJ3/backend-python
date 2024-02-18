from starlette.responses import JSONResponse
from pydantic import BaseModel

from app.services.finding_matching_mkeywords import moodKeywords_sentence_to_our_keywords
from app.services.tockenizing_foodcategory import tockenizing_foodcategory
from app.services.recommnad_one import restaurants_for_one
from app.services.recommnad_two_sklearn import restaurants_for_many
from app.services.restaurants_within_onek import api_restaurants_within_onek
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient, UpdateOne
import requests

app = FastAPI()
client = MongoClient(
        'mongodb+srv://jiyoung:jiyoung1234^^@favsniper.gg9uyie.mongodb.net/?retryWrites=true&w=majority')
db = client["sniper"]
collection = db["user_csv"]

# # TODO: 이 몽고에 저장하는 함수 지워도 되는건지 체크하고 지우기.
# def insert_restaurants(restaurants):
#     try:
#         bulk_operations = []  # 업데이트 또는 삽입을 위한 작업 목록
#
#         for restaurant in restaurants:
#             # 기존 `_id`가 있는지 확인
#             existing_restaurant = collection.find_one({"_id": restaurant["_id"]})
#
#             if existing_restaurant:
#                 # 이미 존재하는 경우 업데이트를 위한 작업 추가
#                 bulk_operations.append(
#                     UpdateOne({"_id": restaurant["_id"]}, {"$set": restaurant})
#                 )
#             else:
#                 # 존재하지 않는 경우 삽입을 위해 바로 MongoDB에 추가
#                 collection.insert_one(restaurant)
#
#         # bulk_write를 사용하여 업데이트 및 삽입 작업을 실행
#         if bulk_operations:
#             collection.bulk_write(bulk_operations)
#
#     except Exception as e:
#         raise Exception(f"Error inserting or updating data into MongoDB: {e}")


# 사용자 장소 반경 1km내 식당 리스트
class Restaurants_within_onek(BaseModel):
    userId: str
    base_coords: list


@app.post("/restaurants/withinonek")
async def restaurants_within_onek(restaurants_within_onek: Restaurants_within_onek):
    try:
        rest_id_list = api_restaurants_within_onek(
            restaurants_within_onek)  # nearby_restaurants 변수 추가
        #insert_restaurants(nearby_restaurants)  # nearby_restaurants를 insert_restaurants 함수에 전달
        return JSONResponse(content={"userId": restaurants_within_onek.userId,
                                     "restaurant_id_list": rest_id_list})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 무드키워드 음성 문장
class Moodkeywords_sentence(BaseModel):
    userId: str
    sentence: str


@app.post("/keywords/mood/speech")
async def process_moodkeywords(moodkeywords_sentence: Moodkeywords_sentence):
    processed_result = moodKeywords_sentence_to_our_keywords(moodkeywords_sentence.sentence)

    return JSONResponse(content={"userId": moodkeywords_sentence.userId,
                                "words": processed_result})


async def request_onek_rest_list_to_redis(roomId):
    url = "http://43.203.17.229:8080/api/restaurants/simple"
    room_id = roomId

    headers = {'Content-Type': 'application/json'}
    params = {"roomId": room_id}
    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        result_data = response.json()
        print(result_data)
        return result_data
    else:
        print("request to redis server has failed!!", response.status_code)

# 확정된 무드키워드로 추천 식당 요청
class Recommand_for_one(BaseModel):
    userId: str
    roomId: str
    moodKeywords: list
    categories: list


@app.post("/restaurants/forone")
async def recommand_for_one(recommand_for_one: Recommand_for_one):
    redis_result = await request_onek_rest_list_to_redis(recommand_for_one.roomId)
    # print("redis_result::::::", redis_result)
    processed_result = restaurants_for_one(recommand_for_one, redis_result)

    return JSONResponse(content={"userId": recommand_for_one.userId,
                                "restaurant_id_list": processed_result})


class Foodcategories_senctence(BaseModel):
    userId: str
    sentence: str


@app.post("/foodcategories/speech")
async def process_foodcategories(foodcategories_senctence: Foodcategories_senctence):
    processed_result = tockenizing_foodcategory(foodcategories_senctence.sentence)

    return JSONResponse(content={"userId": foodcategories_senctence.userId,
                                 "words": processed_result})


# 교집합 추천 식당 요청
class Recommand_for_many(BaseModel):
    userId: str
    restaurant_id_list: list
    user_coords: str


@app.post("/restaurants/formany")
async def recommand_for_many(recommand_for_many: Recommand_for_many):
    num_users = 4
    center_res = []
    processed_result = []
    processed_result_1 = []
    processed_result_2 = []
    processed_result_1[0] = restaurants_for_many(recommand_for_many.restaurant_id_list[:2])
    processed_result_2[1] = restaurants_for_many(recommand_for_many.restaurant_id_list[2:])
    center_res = restaurants_for_many(processed_result_1 + processed_result_2)



    for i in range(num_users):
        processed_result.append(restaurants_for_many(center_res + recommand_for_many.restaurant_id_list[i]))


    return JSONResponse(content={"userId": recommand_for_many.userId,
                                "restaurant_id_list": processed_result})