import math
import heapq

import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import pairwise_distances, cosine_similarity


# # Data & Tables preparation

# Function to read csv files.
def read_file_csv(file_name):
    return pd.read_csv(file_name, encoding="ISO-8859-1")


# Our data.
books_df = read_file_csv('./books.csv')
books_tags_df = read_file_csv('./books_tags.csv')

users_df = read_file_csv('./users.csv')
ratings_df = read_file_csv('./ratings.csv')
tags_df = read_file_csv('./tags.csv')

test_df = read_file_csv('./test.csv')


# Book with ratings and users dataframe.
global b_r_u_df
b_r_u_df = pd.merge(books_df[['book_id', 'title']], ratings_df, on='book_id', how='inner')
b_r_u_df = pd.merge(b_r_u_df, users_df, on='user_id', how='inner')

global items_df
items_df = b_r_u_df[['book_id', 'title']].drop_duplicates(subset='book_id')




# # Non-Personalized

# Score for each book. Explained in the report.
def weighted_average_rating(counts_df, m, rating_mean_df, rating_all_mean):
    return (counts_df / (counts_df + m)) * rating_mean_df + (m / (counts_df + m)) * rating_all_mean


# To get the top k recommendations. The k books with the best score.
def get_top_k_recommendations(df, counts_df, k, columns, m):
    return df[counts_df >= m].nlargest(k, columns)

# We'll need this function for the recommendations according to the age.
# Gets a number and creates the range of ages as required in the task.
def get_age_range(age):
    if age % 10 == 0:
        age -= 1

    lower_bound = age - ((age % 10) - 1)
    upper_bound = age + (10 - (age % 10))

    return lower_bound, upper_bound


# Creates distribution of votes and ratings by book id and returns them.
def merge_tables(df):
    # Dataframe that contains distribution of votes by book ID.
    nb_voters_data = df['book_id'].value_counts()
    nb_voters_df = pd.DataFrame(data={'book_id': nb_voters_data.index.tolist(), 'counts': nb_voters_data.values.tolist()})

    # Dataframe that contains distribution of rate averages by book ID.
    rating_mean_data = df.groupby(['book_id'])['rating'].mean()
    rating_mean_df = pd.DataFrame(data={'book_id': rating_mean_data.index.tolist(), 'rating_mean': rating_mean_data.values.tolist()})
    
    return nb_voters_df, nb_voters_data, rating_mean_df, rating_mean_data


# m represents the minimum voters we need to count the rating and the score. 
# We'll also need the total mean to caluculate the score (WR).
def get_voters_and_means(nb_voters_data, rating_mean_df):
    m = nb_voters_data.quantile(0.90)
    rating_all_mean = rating_mean_df['rating_mean'].mean()
    return m, rating_all_mean


# Get the top k recommendations: the k books with the best weighted average rating.
def calculate_WAR_and_top_k(df, m, rating_all_mean, k, columns):
    df['weighted_average_rating'] = weighted_average_rating(df['counts'], m, df['rating_mean'], rating_all_mean)
    return get_top_k_recommendations(df, df['counts'], k, columns, m)


# ## get_simply_recommendation

# Calculate the WAR and get the k books with the best results.
def get_simply_recommendation(k):
    global b_r_u_df
    
    nb_voters_df, nb_voters_data, rating_mean_df, rating_mean_data = merge_tables(b_r_u_df)
    m, rating_all_mean = get_voters_and_means(nb_voters_data, rating_mean_df)
    
    df = pd.merge(items_df, nb_voters_df, on='book_id', how='inner')
    df = pd.merge(df, rating_mean_df, on='book_id', how='inner')

    return calculate_WAR_and_top_k(df, m, rating_all_mean, k, ['weighted_average_rating'])


recommendation_df = get_simply_recommendation(10)
print(recommendation_df[['book_id','title','weighted_average_rating']].head(10))


# ## get_simply_place_recommendation

# Calculate the WAR and get the k best books by a place.
def get_simply_place_recommendation(place, k):
    global b_r_u_df
    
    b_r_u_place_df = b_r_u_df[b_r_u_df['location'] == place]
    
    nb_voters_df, nb_voters_data, rating_mean_df, rating_mean_data = merge_tables(b_r_u_place_df)
    m, rating_all_mean = get_voters_and_means(nb_voters_data, rating_mean_df)
    
    df = pd.merge(items_df, nb_voters_df, on='book_id', how='inner')
    df = pd.merge(df, rating_mean_df, on='book_id', how='inner')

    return calculate_WAR_and_top_k(df, m, rating_all_mean, k, ['weighted_average_rating'])


place_recommendation_df = get_simply_place_recommendation('Ohio', 10)
print(place_recommendation_df[['book_id','title','weighted_average_rating']].head(10))


# ## get_simply_age_recommendation

# Calculate the WAR and get the k best books by a range of ages.
def get_simply_age_recommendation(age, k):
    global b_r_u_df
    
    lower_bound, upper_bound = get_age_range(age)
    b_r_u_age_df = b_r_u_df[(b_r_u_df['age'] >= lower_bound) & (b_r_u_df['age'] <= upper_bound)]
    
    nb_voters_df, nb_voters_data, rating_mean_df, rating_mean_data = merge_tables(b_r_u_age_df)
    m, rating_all_mean = get_voters_and_means(nb_voters_data, rating_mean_df)
    
    df = pd.merge(items_df, nb_voters_df, on='book_id', how='inner')
    df = pd.merge(df, rating_mean_df, on='book_id', how='inner')

    return calculate_WAR_and_top_k(df, m, rating_all_mean, k, ['weighted_average_rating'])


age_recommendation_df = get_simply_age_recommendation(28, 10)
print(age_recommendation_df[['book_id','title','weighted_average_rating']].head(10))



# # Collaborative Filtering

# Get top K values from given array.
def keep_top_k(array, k):
    smallest = heapq.nlargest(k, array)[-1]
    array[array < smallest] = 0
    return array


# Similirity matrix according to the chosen similarity.
def build_CF_prediction_matrix(sim):
    global ratings_diff
    return 1-pairwise_distances(ratings_diff, metric=sim)


# Function that extracts user recommendations.
# Gets the highest rates indexes and returns book id and the title for that user.
def get_CF_final_output(pred, data_matrix, user_id, items_new_to_original, items, k):
    user_id = user_id - 1
    predicted_ratings_row = pred[user_id]
    data_matrix_row = data_matrix[user_id]
    
    predicted_ratings_unrated = predicted_ratings_row.copy()
    predicted_ratings_unrated[~np.isnan(data_matrix_row)] = 0

    idx = np.argsort(-predicted_ratings_unrated)
    sim_scores = idx[0:k]
    
    # When getting the results, we map them back to original book ids.
    books_original_indexes_df = pd.DataFrame(data={'book_id': [items_new_to_original[index] for index in sim_scores]})
    return pd.merge(books_original_indexes_df, items, on='book_id', how='inner')


# # Get the collaborative filtering recommendation according to the user.
def get_CF_recommendation(user_id, k):
    # Import global variables.
    global ratings_df
    global items_df

    # Declare of global variables.
    global users_original_to_new
    global users_new_to_original
    global items_original_to_new
    global items_new_to_original
    global data_matrix
    global mean_user_rating

    # Part 1.
    unique_users = ratings_df['user_id'].unique()
    unique_items = ratings_df['book_id'].unique()
    n_users = unique_users.shape[0]
    n_items = unique_items.shape[0]

    # Working on user data.
    unique_users.sort()
    # Creating a dictionary that contains a mapping from original user id to a new user id.
    users_original_to_new = {original_index: new_index for original_index, new_index in zip(unique_users, range(n_users))}
    # Creating a dictionary that contains a mapping from new user id to a original user id.
    users_new_to_original = {value: key for key, value in users_original_to_new.items()}

    # Working on items data.
    unique_items.sort()
    # Creating a dictionary that contains a mapping from original book id to a new book id.
    items_original_to_new = {original_index: new_index for original_index, new_index in zip(unique_items, range(n_items))}
    # Creating a dictionary that contains a mapping from new book id to a original book id.
    items_new_to_original = {value: key for key, value in items_original_to_new.items()}

    # Part 2.
    data_matrix = np.empty((n_users, n_items))
    data_matrix[:] = np.nan
    for line in ratings_df.itertuples():
        user = users_original_to_new[line[1]]
        book = items_original_to_new[line[2]]
        rating = line[3]
        data_matrix[user, book] = rating

    mean_user_rating = np.nanmean(data_matrix, axis=1).reshape(-1, 1)

    global ratings_diff
    ratings_diff = (data_matrix - mean_user_rating)
    ratings_diff[np.isnan(ratings_diff)] = 0

    user_similarity = build_CF_prediction_matrix('cosine')
    user_similarity = np.array([keep_top_k(np.array(arr), k) for arr in user_similarity])
    pred = mean_user_rating + user_similarity.dot(ratings_diff) / np.array([np.abs(user_similarity).sum(axis=1)]).T

    # Part 3.
    return get_CF_final_output(pred, data_matrix, user_id, items_new_to_original, items_df, k)


recommendations_by_user = get_CF_recommendation(user_id=1, k=10)
print(recommendations_by_user.head(10))



# # Contact Based Filtering

# Preparing the dataframe for the algorithm.
# Reading the tags and the relevant features and preparing the features for the algorithm.
bookreads_tags_df = pd.merge(books_tags_df, tags_df, on='tag_id', how='inner')

groupped_data = bookreads_tags_df.groupby('goodreads_book_id', as_index=False)['tag_name'].transform(lambda x: ' '.join(x))
books_tags_row_df = pd.DataFrame(data={'goodreads_book_id': groupped_data.index.tolist(), 'tag_name': groupped_data['tag_name'].values.tolist()})

global contact_based_filtering_df
contact_based_filtering_df = pd.merge(books_df[['book_id', 'title', 'authors', 'goodreads_book_id',  'language_code', 'original_title']], books_tags_row_df, on='goodreads_book_id', how='outer')
contact_based_filtering_df['tag_name'] = contact_based_filtering_df['tag_name'].fillna('')


# Clean the data to get lower case letter and get rid of '-'.
def clean_data(x):
    x = str.lower(str(x))
    return x.replace('-', '')


# Get all of our features together with a space in between. The choice of the features is explained in the report.
def create_soup(x):
    return x['original_title'] + ' ' + x['language_code'] + ' ' + x['authors'] + ' ' + x['tag_name']


# Similarity matrix. We use cosine similarity
def build_contact_sim_metrix():
    global count_matrix
    return cosine_similarity(count_matrix, count_matrix)


# We return the top k recommendation according to the content (The features of each book).
def get_contact_recommendation(book_name, k):
    global contact_based_filtering_df

    features = ['original_title', 'language_code', 'authors', 'tag_name']
    for feature in features:
        contact_based_filtering_df[feature] = contact_based_filtering_df[feature].apply(clean_data)

    contact_based_filtering_df['soup'] = contact_based_filtering_df.apply(create_soup, axis=1)

    global count_matrix
    count_matrix = CountVectorizer(stop_words='english').fit_transform(contact_based_filtering_df['soup'])

    cosine_sim = build_contact_sim_metrix()

    contact_based_filtering_df = contact_based_filtering_df.reset_index()
    indices = pd.Series(contact_based_filtering_df.index, index=contact_based_filtering_df['title'])

    idx = indices[book_name]

    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:k+1]

    book_indices = [i[0] for i in sim_scores]
    return contact_based_filtering_df['title'].iloc[book_indices]

contact_based_filtering_result = get_contact_recommendation('Twilight (Twilight, #1)', k=10)
print(contact_based_filtering_result)


# # Section 4 - Questions

# Filter the data. We want only the books with ratings >= 4 and the users that that ranked books at least 10 times.
high_rate_test_df = test_df[test_df['rating'] >= 4]
user_value_counts = high_rate_test_df['user_id'].value_counts()
user_value_counts_df = pd.DataFrame(data={'user_id': user_value_counts.index.tolist(), 'appearances': user_value_counts.values.tolist()})
user_value_counts_df = user_value_counts_df[user_value_counts_df['appearances'] >= 10]


# Evaluation P@k for each similarity.
def precision_k(k):
    # Importing global variables that has been assigned before to use them here.
    global items_df
    global data_matrix
    global ratings_diff
    global mean_user_rating
    global items_new_to_original

    pk_list = []
    for sim in ['cosine', 'euclidean', 'jaccard']:
        calculations_list = []

        user_similarity = 1-pairwise_distances(ratings_diff, metric=sim)
        user_similarity = np.array([keep_top_k(np.array(arr), k) for arr in user_similarity])
        pred = mean_user_rating + user_similarity.dot(ratings_diff) / np.array([np.abs(user_similarity).sum(axis=1)]).T

        for user_id in user_value_counts_df['user_id'].values:
            user_recommendations = get_CF_final_output(pred, data_matrix, user_id, items_new_to_original, items_df, k)

            counter = 0
            for book_idx in user_recommendations['book_id'].values:
                chosen_book = high_rate_test_df[(high_rate_test_df['user_id'] == user_id) & (high_rate_test_df['book_id'] == book_idx)]
                if chosen_book.shape[0] == 1:
                    counter += 1

            calculations_list.append(counter / k)

        pk_list.append(sum(calculations_list) / user_value_counts_df.shape[0])

    return pk_list

print(precision_k(10))


# Evaluation ARHR.
def ARHR(k):
    # Importing global variables that has been assigned before to use them here.
    global items_df
    global data_matrix
    global ratings_diff
    global mean_user_rating
    global items_new_to_original

    arhr_list = []
    for sim in ['cosine', 'euclidean', 'jaccard']:
        calculations_list = []

        user_similarity = 1-pairwise_distances(ratings_diff, metric=sim)
        user_similarity = np.array([keep_top_k(np.array(arr), k) for arr in user_similarity])
        pred = mean_user_rating + user_similarity.dot(ratings_diff) / np.array([np.abs(user_similarity).sum(axis=1)]).T

        for user_id in user_value_counts_df['user_id'].values:
            user_recommendations = get_CF_final_output(pred, data_matrix, user_id, items_new_to_original, items_df, k)

            user_high_rate_df = high_rate_test_df[high_rate_test_df['user_id'] == user_id]
            user_rec_merged_df = pd.merge(user_recommendations, user_high_rate_df, on='book_id', how='inner')

            for position in user_rec_merged_df.index + 1:
                calculations_list.append(1 / position)

        arhr_list.append(sum(calculations_list) / user_value_counts_df.shape[0])
        
    return arhr_list


print(ARHR(10))



# Helper function to build the function RMSE. This time we wont filter the data.
def get_recommendations_RMSE(pred, data_matrix, user_id):
    user_id = user_id - 1
    predicted_ratings_row = pred[user_id]
    data_matrix_row = data_matrix[user_id]

    predicted_ratings_unrated = predicted_ratings_row.copy()
    predicted_ratings_unrated[~np.isnan(data_matrix_row)] = 0

    book_ids = np.argsort(-predicted_ratings_unrated)
    books_rating = np.sort(predicted_ratings_unrated)[::-1]

    return {idx: rating for idx, rating in zip(book_ids, books_rating)}


# Evaluation RMSE.
def RMSE():
    # Importing global variables that has been assigned before to use them here.
    global ratings_diff
    global mean_user_rating

    rmse_list = []
    for sim in ['cosine', 'euclidean', 'jaccard']:
        sum_error = 0
        count_lines = 0

        user_similarity = 1-pairwise_distances(ratings_diff, metric=sim)
        pred = mean_user_rating + user_similarity.dot(ratings_diff) / np.array([np.abs(user_similarity).sum(axis=1)]).T

        for user_id, test_user_data in test_df.groupby('user_id'):
            user_recommendations = get_recommendations_RMSE(pred, data_matrix, user_id)
            for row in test_user_data.itertuples(index=False):
                _, test_book_id, rating = tuple(row)
                prediction = user_recommendations[test_book_id] if test_book_id in user_recommendations else 0

                if prediction == 0:
                    continue

                sum_error += (prediction - rating)**2
                count_lines += 1

        rmse_list.append(math.sqrt(sum_error/count_lines))

    return rmse_list


print(RMSE())