#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <cctype>

using namespace std;

// Функция для извлечения паролей из строки
vector<string> extractPasswords(const string& filename) {
    vector<string> passwords;
    ifstream file(filename, ios::binary);
    
    if (!file.is_open()) {
        cerr << "Не удалось открыть файл: " << filename << endl;
        return passwords;
    }
    
    string line;
    string currentPassword;
    bool inPassword = false;
    
    // Читаем файл построчно
    while (getline(file, line)) {
        // Ищем шаблон "password": "xxx"
        size_t pos = line.find("\"password\": \"");
        if (pos != string::npos) {
            pos += 13; // Длина "\"password\": \""
            size_t endPos = line.find('"', pos);
            if (endPos != string::npos) {
                string password = line.substr(pos, endPos - pos);
                // Проверяем, что пароль имеет правильный формат
                if (password.length() > 10) {
                    passwords.push_back(password);
                }
            }
        }
    }
    
    file.close();
    return passwords;
}

// Функция для определения самого частого символа на каждой позиции
string findMostCommonPassword(const vector<string>& passwords) {
    if (passwords.empty()) {
        return "";
    }
    
    // Определяем длину пароля (все пароли должны быть одинаковой длины)
    size_t passwordLength = passwords[0].length();
    
    // Проверяем, что все пароли имеют одинаковую длину
    for (const auto& p : passwords) {
        if (p.length() != passwordLength) {
            cerr << "Внимание: пароли имеют разную длину!" << endl;
            passwordLength = min(passwordLength, p.length());
        }
    }
    
    string result(passwordLength, ' ');
    
    // Для каждой позиции
    for (size_t pos = 0; pos < passwordLength; pos++) {
        map<char, int> charCount;
        
        // Считаем символы на данной позиции
        for (const auto& password : passwords) {
            if (pos < password.length()) {
                char c = password[pos];
                charCount[c]++;
            }
        }
        
        // Находим самый частый символ
        char mostFrequent = ' ';
        int maxCount = 0;
        
        for (const auto& pair : charCount) {
            if (pair.second > maxCount) {
                maxCount = pair.second;
                mostFrequent = pair.first;
            }
        }
        
        result[pos] = mostFrequent;
        
        // Выводим статистику для каждой позиции
        cout << "Позиция " << pos + 1 << ": ";
        for (const auto& pair : charCount) {
            cout << "'" << pair.first << "'=" << pair.second << " ";
        }
        cout << "-> наиболее частый: '" << mostFrequent << "' (" << maxCount << " раз)" << endl;
    }
    
    return result;
}

// Функция для проверки, является ли пароль валидным (соответствует формату)
bool isValidPassword(const string& password) {
    if (password.length() < 15) return false;
    
    // Проверяем формат: 5 символов_5 символов_5 символов
    int underscoreCount = 0;
    for (char c : password) {
        if (c == '_') underscoreCount++;
    }
    
    return underscoreCount == 2;
}

int main() {
    string filename = "task.txt";
    
    cout << "Извлечение паролей из файла " << filename << "..." << endl;
    vector<string> passwords = extractPasswords(filename);
    
    if (passwords.empty()) {
        cerr << "Пароли не найдены!" << endl;
        return 1;
    }
    
    cout << "Найдено паролей: " << passwords.size() << endl << endl;
    
    // Фильтруем только валидные пароли (с нужным форматом)
    vector<string> validPasswords;
    for (const auto& p : passwords) {
        if (isValidPassword(p)) {
            validPasswords.push_back(p);
        }
    }
    
    cout << "Валидных паролей: " << validPasswords.size() << endl << endl;
    
    if (validPasswords.empty()) {
        cerr << "Нет валидных паролей!" << endl;
        return 1;
    }
    
    // Выводим первые 10 паролей для проверки
    cout << "Примеры паролей (первые 10):" << endl;
    for (size_t i = 0; i < min(10, (int)validPasswords.size()); i++) {
        cout << validPasswords[i] << endl;
    }
    cout << endl;
    
    // Находим самый частый пароль по позициям
    cout << "Анализ частоты символов на каждой позиции:" << endl;
    string mostCommonPassword = findMostCommonPassword(validPasswords);
    
    cout << "\n========================================" << endl;
    cout << "Восстановленный пароль: " << mostCommonPassword << endl;
    cout << "========================================" << endl;
    
    return 0;
}
