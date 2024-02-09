import numpy as np
import pandas as pd
from bson import ObjectId
from haversine import haversine, Unit
from pymongo import MongoClient
from gensim.models import Word2Vec

'''
### 1KM 내의 'foodCategory'와 'moodKeyword'에 유사도 가장 가까운 식당 3개

`F→B(nest)→B(python)` 미국식,[“힙한”, ”분위기좋은”, ”차분한”], 위치(주소, 위도경도)
`B(python)→B(nest)→ F` 맵핑되는 식당 3개

1. 위치로부터 1km 내 레스토랑 리스트 꾸리기
2. 카테고리로 2차 거르기
    nearby_restaurants의 foodCategory를 전부 조회하여 user의 카테고리와 같은 식당 리스트 추리기
3. 유저 분위기태그 벡터라이징 
4. 유저 분위기태그 벡터와 유사한 벡터3개 꾸리기
'''
# float로 형변환하는 함수
def to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

user_vectors = []
def vectorizing_user_moodKeywords(given_moods):
    # Word2Vec 모델 로드
    model_path = '/Users/finallyfinn/Desktop/projects/krafton/backend-python/app/assets/mymodelfromreviews/updated_model.model'
    model = Word2Vec.load(model_path)

    for mood_keyword in given_moods:
        print('mood_keyword in given_moods: ',mood_keyword)
        mood_vector = []

        for keyword in mood_keyword.split(','):
            # 대괄호, 세미콜론, 작은 따옴표 제거
            keyword = keyword.replace('[', '').replace(']', '').replace(';', '').replace("'", "").strip()

            # 모델의 vocabulary에 있는 단어에 대해서만 처리
            try:
                if keyword and keyword in model.wv:
                    mood_vector.append(model.wv[keyword])
            except KeyError:
                print(f"Ignoring '{keyword}' as it is not present in the vocabulary.")

        # 모델 vocabulary에 있는 단어가 없으면 most_similar을 통해 대체값 사용
        if not mood_vector and mood_keyword:
            # 대괄호, 세미콜론 제거
            mood_keyword = mood_keyword.replace('[', '').replace(']', '').replace(';', '').strip()

            # 모델 vocabulary에 있는지 확인 후 처리
            if mood_keyword in model.wv:
                similar_words = model.wv.most_similar(positive=[mood_keyword], topn=5)
                for similar_word, _ in similar_words:
                    similar_word = similar_word.strip()
                    # 작은 따옴표 제거
                    similar_word = similar_word.replace("'", "")
                    try:
                        if similar_word and similar_word in model.wv:
                            mood_vector.append(model.wv[similar_word])
                    except KeyError:
                        print(f"Ignoring '{similar_word}' as it is not present in the vocabulary.")

        # 여러 벡터를 압축하여 하나의 벡터로 만듭니다. (평균 사용)
        compressed_vector = sum(mood_vector) / len(mood_vector) if mood_vector else None
        # If compressed_vector is not None, convert it to a string with commas between values
        if compressed_vector is not None:
            vector_str = '[' + ', '.join(map(str, compressed_vector)) + ']'
        else:
            vector_str = None

        user_vectors.append(vector_str)
        print('vectorized!')
        print('user_vectors: ',user_vectors)
        return user_vectors

# 모든 벡터 간의 유클리드 거리를 계산하는 함수
def calculate_euclidean_distance(user_vector, rest_vector):
    if len(user_vector) != len(rest_vector):
        raise ValueError("Vector dimensions do not match.")
    distance = np.linalg.norm(np.array(user_vector) - np.array(rest_vector))
    return distance

# API
def restaurants_for_one(recommand_for_one):
    user_id = recommand_for_one.userId
    given_category_list = recommand_for_one.categories
    given_moods = recommand_for_one.moodKeywords

    cate_filtered_nearby_rests = []

    # MongoDB 연결
    client = MongoClient(
        'mongodb+srv://jiyoung:jiyoung1234^^@favsniper.gg9uyie.mongodb.net/?retryWrites=true&w=majority')
    db = client['sniper']
    collection = db['user_csv']

    # MongoDB에서 식당 데이터 가져오기
    nearby_restaurants = collection.find()

    # 사용자가 입력한 카테고리와 일치하는 식당 필터링
    for restaurant in nearby_restaurants:
        for category in given_category_list:
            if restaurant.get('food_category') == category or restaurant.get('foodCategories') == category:
                cate_filtered_nearby_rests.append(restaurant)

    print(f'1km 이내의 카테고리에 속하는 식당 수: {len(cate_filtered_nearby_rests)}')

    # 유저 분위기 태그 벡터화
    vectorizing_user_moodKeywords(given_moods)

    user_vector_str = user_vectors[0]  # TODO: user_vectors 변수명 수정
    user_vector_list = eval(user_vector_str)
    user_vector = [float(num) for num in user_vector_list]

    # 유사한 식당 찾기
    for rest in cate_filtered_nearby_rests:
        rest_vector = eval(rest['vector'])
        rest['res_distance'] = calculate_euclidean_distance(user_vector, rest_vector)

    # 가장 유사한 식당들 선택
    four_res_list = sorted(cate_filtered_nearby_rests, key=lambda x: x['res_distance'])[:4]
    four_id_list = []

    for res in four_res_list:
        print("Recommended restaurant name: ", res['name'])
        four_id_list.append(res['_id'])

    return four_id_list


