package com.todo.todoapi.controller;

import com.todo.todoapi.dto.TodoCreateRequest;
import com.todo.todoapi.entity.Todo;
import com.todo.todoapi.service.TodoService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/todos")
@RequiredArgsConstructor
public class TodoController {
    private final TodoService todoService;

    @GetMapping
    public List<Todo> findAll(){
        return todoService.findAll();
    }
    @PostMapping
    public Todo save(@RequestBody TodoCreateRequest request){
        return todoService.save(request);
    }
}
