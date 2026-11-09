from index_common import Searcher
from search_index import show

CASES = [
    ("На какой планете родился Yarwyn Daelthos?", "yarwyn-daelthos.md", "Tevlan"),
    ("Who was the apprentice of Yarwyn Daelthos?", "yarwyn-daelthos.md", "Tevzek Caenor"),
    ("Что такое Void Core и какое оружие на нём было?", "rk-8-orbital-battle-station.md", "megabeam"),
    ("Из чего сделан плазменный клинок и кто им пользовался?", "plasmablade.md", "ixium"),
    ("Какая ледяная планета является родиной вида snowfang?", "havrmara.md", "snowfang"),
    ("Which planet has two suns and moisture farms?", "tevlan.md", "moisture"),
    ("How did the Vastrian Dominion fall after Ursera Bregoth died?", "ascendant-directorate.md", "fell"),
    ("Кто такой Tevzek Caenor и почему он покинул орден Salphos?", "tevzek-caenor.md", "Salphos"),
]
NEGATIVE = [
    "Как приготовить борщ?",
    "Who is Darth Vader?",
    "Расскажи про Люка Скайуокера и планету Татуин",
]


def main():
    searcher = Searcher()
    first = third = answered = 0
    for query, expected, keyword in CASES:
        results = searcher.search(query, 3)
        sources = [chunk["source"].split("/")[-1] for chunk in results]
        hit_first = sources[0] == expected
        hit_third = expected in sources
        has_answer = any(keyword.lower() in chunk["text"].lower() for chunk in results)
        first += hit_first
        third += hit_third
        answered += has_answer
        print(f"\nQ: {query}\nexpected: {expected}, keyword: {keyword}")
        print(f"top1 hit: {hit_first}, top3 hit: {hit_third}, answer text in top3: {has_answer}")
        show(results)
    total = len(CASES)
    print(f"\nSUMMARY: top1 {first}/{total}, top3 {third}/{total}, answer in top3 {answered}/{total}")
    print("\nQUERIES WITHOUT ANSWER IN THE KNOWLEDGE BASE")
    for query in NEGATIVE:
        results = searcher.search(query, 3)
        print(f"\nQ: {query}")
        show(results)


if __name__ == "__main__":
    main()
