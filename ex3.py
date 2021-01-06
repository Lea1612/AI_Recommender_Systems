import seaborn as sns
import pandas as pd

def read_file_csv(file_name):
    return pd.read_csv(file_name, low_memory=False, encoding = "ISO-8859-1")

# Calculate the weighted average rating = [(v/(v+m))*R] + [(m/(v+m))*C]
def weighted_average_rating(nb_voters, rating_mean, rating_mean_all, m):
    return ((nb_voters / (nb_voters + m)) * rating_mean) + ((m / (nb_voters + m)) * rating_mean_all)

def main():
    books_data = "data/books.csv"
    ratings_data = "data/ratings.csv"
    pandas_data_books = read_file_csv(books_data)
    pandas_data_ratings = read_file_csv(ratings_data)
    print(pandas_data_ratings.head(4))

    # Calculate nb of voters for each book - v
    nb_voters_book = pandas_data_ratings['book_id'].value_counts()
    # print(nb_voters_book[28])
    
    # Calculate the rating mean for each book - R
    rating_mean_book = pandas_data_ratings.groupby(['book_id'])[['rating']].mean()
    # print(rating_mean_book)

    # Fix the number of minimum readers to get into the list - m 
    m = nb_voters_book.quantile(0.90)
    # print(m)

    # Rating mean (all of the books) - C.
    rating_all_mean = pandas_data_ratings['rating'].mean()
    # print(rating_all_mean)

    # Calculate the weighted average rating = [(v/(v+m))*R] + [(m/(v+m))*C]
    # For each book, get this rating.

    # weighted_rating = {}
    # for i in nb_voters_book:
    #     if rating_mean_book[i] > m :
    #         weighted_rating[i] = weighted_average_rating(nb_voters_book[i], rating_mean_book[i], rating_all_mean, m)

   
    # print(weighted_rating)


if __name__ == "__main__":
    main()