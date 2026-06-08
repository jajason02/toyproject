package com.todo.todoapi.service;

import com.todo.todoapi.dto.TodoCreateRequest;
import com.todo.todoapi.entity.Todo;
import com.todo.todoapi.repository.TodoRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class TodoService {
    private final TodoRepository todoRepository;

    public List<Todo> findAll() {
        return todoRepository.findAll();
    }
    public Todo save(TodoCreateRequest request) {
        Todo todo = Todo.builder()
                .userId(request.getUserId())
                .content(request.getContent())
                .createdAt(LocalDateTime.now())
                .finished(false)
                .build();
        return todoRepository.save(todo);
    }
}
