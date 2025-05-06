import {Component, EventEmitter, Output} from '@angular/core';
import {Dialog} from 'primeng/dialog';
import {Button} from 'primeng/button';
import {InputText} from 'primeng/inputtext';
import {TaskInfo} from '../../domain/task-info';
import {FormControl, FormGroup, ReactiveFormsModule, Validators} from '@angular/forms';

@Component({
  selector: 'app-new-task-dialog',
  imports: [
    Dialog,
    Button,
    InputText,
    ReactiveFormsModule
  ],
  templateUrl: './new-task-dialog.component.html',
  styleUrl: './new-task-dialog.component.css'
})
export class NewTaskDialogComponent {
  visible = false;
  @Output() confirmNewTask = new EventEmitter<TaskInfo>();
  @Output() cancelNewTask = new EventEmitter<void>();

  formGroup!: FormGroup;

  ngOnInit() {
    this.formGroup = new FormGroup({
      taskId: new FormControl('', {nonNullable: true, validators: [Validators.required]}),
      operator: new FormControl('')
    });
  }

  showDialog() {
    this.formGroup.reset();
    this.formGroup.get('taskId')?.setValue('Task-' + Date.now().toString());
    this.formGroup.get('operator')?.setValue('默认操作员');
    this.visible = true;

  }

  createTask() {
    if (this.formGroup.invalid) {
      this.formGroup.markAllAsTouched();
      return;
    }

    const taskInfo: TaskInfo = {
      taskId: this.formGroup.get('taskId')?.value,
      operator: this.formGroup.get('operator')?.value,
      time: new Date()
    };
    this.confirmNewTask.emit(taskInfo);

    this.visible = false;
  }

  cancelTask() {
    this.cancelNewTask.emit();
    this.visible = false;
  }
}
