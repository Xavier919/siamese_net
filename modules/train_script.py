from sklearn.model_selection import train_test_split
import argparse
import torch
from modules.preprocess import text_edit
from modules.utils import *
from modules.model import BaseNet1D, SiameseNetwork
from gensim.models import KeyedVectors
from modules.dataloader import PairedWord2VecDataset
from torch.utils.data import DataLoader
import torch.optim as optim

parser = argparse.ArgumentParser()
parser.add_argument("num_samples", type=int)
parser.add_argument("batch_size", type=int)
parser.add_argument("epochs", type=int)
parser.add_argument("lr", type=float)
parser.add_argument("max_len", type=int)
args = parser.parse_args()


if __name__ == "__main__":

    dataset = build_dataset(path="siamese_net/data",num_samples=args.num_samples, rnd_state=10)

    dataset = text_edit(dataset,grp_num=False,rm_newline=True,rm_punctuation=True,lowercase=True,lemmatize=False,html_=False,convert_entities=False,expand=False)

    X = [x['text'] for x in dataset.values() if x['section_1'] in ['actualites', 'sports', 'affaires', 'arts', 'international']]
    Y = [x['section_label'] for x in dataset.values() if x['section_1'] in ['actualites', 'sports', 'affaires', 'arts', 'international']]

    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

    model_path = 'wiki.fr.vec'
    word2vec_model = KeyedVectors.load_word2vec_format(model_path, binary=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using {device} device")

    text = "Ceci est un texte exemple"
    vector = text_to_word2vec(text, word2vec_model)
    shape = vector.shape[0]

    train_dataset = PairedWord2VecDataset(X_train, Y_train, text_to_word2vec, word2vec_model, 50000)
    train_loader = DataLoader(train_dataset, args.batch_size, shuffle=True)

    test_dataset = PairedWord2VecDataset(X_test, Y_test, text_to_word2vec, word2vec_model, 10000)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size)

    base_net = BaseNet1D(input_channels=300, sequence_length=10000)
    siamese_model = SiameseNetwork(base_net)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    optimizer = optim.RMSprop(siamese_model.parameters(), lr=args.lr)

    epochs = args.epochs
    best_accuracy = 0
    for epoch in range(epochs):
        train_loss = train_epoch(siamese_model, train_loader, optimizer, device)
        val_accuracy = eval_model(siamese_model, train_loader, device)
        print(f"Epoch {epoch}, Train Loss: {train_loss}, Validation Accuracy: {val_accuracy}")
        
        if val_accuracy > best_accuracy:
            best_accuracy = val_accuracy
            torch.save(siamese_model.state_dict(), 'best_model.pth')
            print("Model saved as best model")
